"""Větné členy z rozboru — role jako doplněk k typům od agentů.

PROČ TO VZNIKLO. Odpovídač uměl čtyři druhy odpovědí: čas, místo, počet
a druh — všechny od agentů. Otázky, na které agent typ nedodá, propadly:

    Co řekl Janovi?      „Janovi" je v rozboru `obl` s `Case=Dat`
    Jak se jmenovaly?    odpovědí je JMÉNO, ale ptáme se JAK
    Komu to dal?         dativ, žádný agent ho neoznačuje

Přitom to v datech leží. Rozbor u každého tokenu říká, jaký je to větný
člen; stačí ho přečíst.

ROLE NENÍ TYP a nenahrazuje ho.

    role   FUNKCE   „který větný člen to je"   z rozboru, tabulkou
    typ    OBSAH    „je to čas / místo"        našel agent

„v Praze" i „v bezvědomí" jsou obojí role `kde`; jen u prvního Topos ověřil,
že je to místo. Proto se typ bere přednostně a role je záchranná síť —
odpoví i tam, kde agent mlčí, jen s menší jistotou.

PŘEVZATO Z conBondu (`roles.py`), kde je katalog o jedenadvaceti rolích
a mapuje se z `deprel` + pád + životnost. Tady je zkrácený na dvanáct, které
odpovídají tázacím tvarům, jež umíme rozpoznat; rozšíření je řádek v JSON,
ne větev v kódu.
"""

from typing import Mapping, Optional, Sequence

from .language import Jazyk


def pad(token: Mapping) -> str:
    for a in token["acts"]:
        if a.startswith("Case="):
            return a.split("=", 1)[1]
    return ""


# Odpověď musí něco nést. „Řekl jim" má správnou roli, ale `jim` neodpovídá
# na nic — a `se` u „jmenovala se" je jen část slovesa. Stejný řez dělá agent
# Druh se svým NEVHODNE_UPOS; je to totéž pravidlo, ne shoda náhod.
PRAZDNE_UPOS = ("PRON", "DET", "PART", "AUX", "PUNCT", "ADP", "SCONJ", "CCONJ")


def deprel(token: Mapping) -> str:
    """Závislost tokenu. V `acts` je hned za slovním druhem, ale jistější je
    vzít první malý řetězec — matice metadat pořadí přeskládá."""
    for a in token["acts"]:
        if a.islower() and "=" not in a:
            return a
    return ""


class Role:
    """Přiřadí tokenům větné členy podle rozboru."""

    def __init__(self, jazyk: Optional[Jazyk] = None):
        self.jazyk = jazyk or Jazyk.nacist()

    def nese_obsah(self, token: Mapping, role: str = "") -> bool:
        """Smí tenhle token odpovídat v téhle roli?

        Dvě síta nad sebou. Prázdná slova neodpovídají nikdy — `jim`, `se`,
        `a`. Jmenné role navíc žádají jméno: na „koho" se neodpovídá
        slovesem, i když ho tam rozbor jako předmět pověsil."""
        upos = token.get("upos")
        if upos in PRAZDNE_UPOS:
            return False
        if role in self.jazyk.role_zadaji_jmeno:
            return upos in self.jazyk.jmenne_upos
        return True

    def predlozka(self, veta: Sequence[Mapping], t: Mapping) -> str:
        for x in veta:
            # `case` u předložky, `mark` u spojky — „na gymnáziu" i „jako
            # učitel" jsou totéž: funkční slovo, které roli teprve určí.
            if x.get("head") == t.get("id") and deprel(x) in ("case", "mark"):
                return x["lemma"].lower() if x.get("lemma") else x["form"].lower()
        return ""

    def role_tokenu(self, token: Mapping, veta: Sequence[Mapping] = ()) -> str:
        """Větný člen jednoho tokenu, nebo prázdno.

        Pád rozhoduje dřív než výchozí hodnota: `obl` je `kde` obecně, ale
        v dativu je to `komu_cemu` — bez pádu by se „řekl Janovi" četlo
        jako určení místa."""
        d = deprel(token)
        tabulka = self.jazyk.deprel_na_roli.get(d)
        if not tabulka:
            return ""
        # Předložka bije pád. „jako učitel" je akuzativ stejně jako
        # „napsal knihu", ale odpovídá na jinou otázku.
        z_predlozky = self.jazyk.predlozka_na_roli.get(self.predlozka(veta, token))
        if z_predlozky:
            return z_predlozky
        p = pad(token)
        r = tabulka.get(p) or tabulka.get("vychozi", "")
        # Některé role stojí a padají s předložkou. Bez věty se neověří,
        # takže se raději nepřiřadí — tvrdit „s kým" o holém instrumentálu
        # je horší než mlčet.
        nutne = self.jazyk.role_vyzaduji_predlozku.get(r)
        if nutne and self.predlozka(veta, token) not in nutne:
            return ""
        return r

    def role_vety(self, veta: Sequence[Mapping]) -> dict:
        """Role → indexy tokenů, které ji ve větě nesou."""
        out: dict = {}
        for i, t in enumerate(veta):
            r = self.role_tokenu(t, veta)
            if r and self.nese_obsah(t, r):
                out.setdefault(r, []).append(i)
        return out

    # ---- otázka ------------------------------------------------------
    def role_otazky(self, text: str, prisudek: str = "") -> str:
        """Jakou roli má mít odpověď na tuhle otázku.

        `prisudek` umí roli přemapovat: u pojmenování se ptáme „jak", ale
        odpovědí je jméno, tedy předmět — a to je vlastnost slovesa, ne
        tázacího tvaru."""
        r = ""
        for tvar in self.jazyk.tvary_otazky(text):
            r = self.jazyk.tazaci_na_roli.get(tvar, "")
            if r:
                break
        if not r:
            return ""
        prepis = self.jazyk.role_podle_prisudku.get(prisudek.lower(), {})
        return prepis.get(r, r)

    def rozsah(self, veta: Sequence[Mapping], i: int) -> list:
        """Token i s tím, co k němu patří: předložka, shodný přívlastek,
        části jména. „na brněnském předměstí Židenice" je jedna odpověď,
        ne čtyři."""
        koren = veta[i]
        rozsah = {i}
        for j, t in enumerate(veta):
            if t.get("head") != koren.get("id"):
                continue
            if deprel(t) in ("case", "amod", "flat", "nummod", "det", "fixed"):
                rozsah.add(j)
        return sorted(rozsah)
