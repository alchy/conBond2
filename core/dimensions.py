"""Rozměry — kódované osy, po kterých se dá rozhodovat, když fakt chybí.

ODKUD TO VZNIKLO. „Mohla Božena Němcová znát Emanuela Halmana?" nemá v korpusu
přímou odpověď a složit ji z hran taky nejde — nikdo o nich nenapsal ani
řetěz. Přesto se odpovědět dá: nemohla, protože zemřela jedenáct let předtím,
než se narodil.

První pokus to řešil dvěma `if`y v Pythonu. To je špatně a v tomhle projektu
se to už umí pojmenovat: **když se v jádře objeví `if` podle druhu dat,
znamená to, že chybí šev** (viz `interfaces.py`). Nebyla to slabina času,
byla to díra v referenčním jazyce — čas nebyl nikdy zakódovaný jako fakt
téhož tvaru jako ostatní.

TŘI PATRA ODPOVĚDI. Rozměr je až to poslední a nastupuje, teprve když
selžou obě předchozí:

    1. přímý fakt     věta to říká                    odpověď
    2. složený fakt   pravidlo z faktů to složí       odvozeno, i s cestou
    3. rozměr         kódovaná osa to rozhodne        vyloučeno

ROZMĚR UMÍ VYVRACET, NE POTVRZOVAT. Tohle je ta věta, kvůli které modul
existuje, a platí pro všechny osy stejně:

    čas       intervaly se nepřekrývají  ⇒ NE      překrývají se  ⇒ nic
    místo     v týž čas jinde            ⇒ NE      totéž místo    ⇒ nic
    počet     tři děti ≠ dvacet          ⇒ NE      shoda          ⇒ nic
    zařazení  ryba a savec se vylučují   ⇒ NE      obojí zvíře    ⇒ nic

Pravá strana je vždycky prázdná a musí být. Že spolu dva lidé žili, o jejich
známosti neříká nic; kdyby z toho rozměr dělal „ano", vyrobil by přesvědčivý
nesmysl na každou dvojici v korpusu. Monotónní pole to dovoluje přesně
v tomhle jednom směru: kladné tvrzení z nepřítomnosti nikdy neplyne, ale
záporné z DOLOŽENÉ neslučitelnosti ano.

ROZMĚR JEN ZNAČKUJE, ROZHODUJÍ DATA. Modul netvrdí, která značka znamená
„nemožné" — to by byl týž zapečený axiom, jen schovaný o patro níž. Rozměr
dvojici jen OZNAČÍ (`disjunktni` / `prekryv` / `neznamo`) a `zmerit()` pak
nad doloženými dvojicemi spočítá, která značka se u nich nevyskytuje. Teprve
to je pravidlo — s číslem za sebou a s protipříklady, když nějaké jsou.

    znal(A, B) doloženo 340×  ·  z toho disjunktni 0  ·  v pozadí 61 %
      ⇒ „disjunktní ⇒ nemožné"   zdvih ∞, protipříkladů 0

Protipříklady jsou k nezaplacení dvakrát: buď pravidlo neplatí, nebo je
špatně datum — a to je rovnou hlásič chyb agenta, který ho vytáhl.
"""

from abc import ABC, abstractmethod
from typing import Any, Iterable, Mapping, Optional, Sequence

# Značka, kterou rozměr dvojici označí. `neznamo` NENÍ hodnota mezi
# ostatními — je to přiznání, že se to z dat nedá říct, a do rozhodování
# proto nevstupuje. Bez téhle třetí značky by neúplná data vyráběla zápory.
DISJUNKTNI, PREKRYV, NEZNAMO = "disjunktni", "prekryv", "neznamo"


class Rozmer(ABC):
    """Osa, po které se dají dvě entity porovnat.

    Implementace dodává dvě věci a ani jednu navíc: jak se hodnota z korpusu
    přečte a jak vypadá vztah dvou hodnot. NEŘÍKÁ, co z toho plyne."""

    jmeno = ""

    @abstractmethod
    def hodnota(self, entita: str) -> Any:
        """Souřadnice entity na téhle ose, nebo None, když se neví."""

    @abstractmethod
    def vztah(self, a: Any, b: Any) -> str:
        """Značka vztahu dvou hodnot: DISJUNKTNI / PREKRYV / NEZNAMO."""

    def znacka(self, a: str, b: str) -> str:
        ha, hb = self.hodnota(a), self.hodnota(b)
        if ha is None or hb is None:
            return NEZNAMO
        return self.vztah(ha, hb)


def zmerit(rozmer: Rozmer, dolozene: Iterable, pozadi: Iterable) -> dict:
    """Která značka se u doložených dvojic NEVYSKYTUJE — a jak je to vzácné.

    `dolozene` jsou dvojice, o kterých korpus tvrdí hledaný vztah („znal se
    s"). `pozadi` jsou dvojice, o kterých netvrdí nic — bez nich se nedá nic
    poznat: kdyby byla `disjunktni` vzácná i v pozadí, neříká její absence
    u doložených vůbec nic.

    Vrací pro každou značku počty a zdvih. Rozhodnutí, co přijmout, patří
    volajícímu, protože prahu je vidět jen odtamtud.
    """
    def rozdelit(dvojice):
        c: dict = {DISJUNKTNI: 0, PREKRYV: 0, NEZNAMO: 0}
        prip: dict = {}
        for a, b in dvojice:
            z = rozmer.znacka(a, b)
            c[z] = c.get(z, 0) + 1
            prip.setdefault(z, []).append((a, b))
        return c, prip

    cd, prip_d = rozdelit(dolozene)
    cp, _ = rozdelit(pozadi)
    # Neznámo se do jmenovatele nepočítá. Dvojice, u které chybí datum,
    # nesvědčí ani pro, ani proti — a kdyby se počítala, ředila by obojí.
    nd = cd[DISJUNKTNI] + cd[PREKRYV]
    np_ = cp[DISJUNKTNI] + cp[PREKRYV]
    out = {"rozmer": rozmer.jmeno, "dolozeno": nd, "pozadi": np_,
           "neznamo_dolozenych": cd[NEZNAMO], "znacky": {}}
    for z in (DISJUNKTNI, PREKRYV):
        podil_d = cd[z] / nd if nd else 0.0
        podil_p = cp[z] / np_ if np_ else 0.0
        out["znacky"][z] = {
            "u_dolozenych": cd[z], "podil_dolozenych": podil_d,
            "podil_pozadi": podil_p,
            # Zdvih pod jednou znamená, že se ta značka u doložených dvojic
            # vyskytuje VZÁCNĚJI než náhodou — a nula znamená, že vůbec.
            "zdvih": (podil_d / podil_p) if podil_p else None,
            # Dvojice s touhle značkou. U značky, která se má u doložených
            # NEvyskytovat, jsou to protipříklady; u té druhé prostě
            # doklady. Jedno pole, protože je to táž informace — pojmenovat
            # je „protipříklady" plošně bylo matoucí.
            "priklady": prip_d.get(z, [])[:5]}
    return out


def vylucujici_znacka(mereni: Mapping, nejvys_podil: float = 0.0,
                      nejmene_dokladu: int = 20) -> Optional[str]:
    """Značka, kterou lze prohlásit za vylučující — nebo None.

    Dvě podmínky a obě jsou nutné. Značka se u doložených dvojic nesmí
    vyskytovat (nad `nejvys_podil`) A musí být na čem to tvrdit: pravidlo
    z pěti dvojic je náhoda, ne zákon. Práh dokladů je tu proto, že mlčení
    malého vzorku vypadá stejně jako zákon.

    Nekontroluje se jen absence, ale i to, že značka v POZADÍ vůbec je.
    Kdyby `disjunktni` neexistovala nikde, její absence u doložených dvojic
    by nic neznamenala — a pravidlo by bylo prázdné.
    """
    for z, d in mereni.get("znacky", {}).items():
        if mereni["dolozeno"] < nejmene_dokladu:
            continue
        if d["podil_dolozenych"] <= nejvys_podil and d["podil_pozadi"] > 0:
            return z
    return None


def rozhodnout(rozmery: Sequence, pravidla: Mapping, a: str, b: str) -> dict:
    """Třetí patro odpovědi: umí některý rozměr tuhle dvojici vyloučit?

    Prochází se všechny osy, protože stačí JEDNA neslučitelnost. Kladné
    tvrzení odtud nikdy nevzejde — nejlepší, co rozměr umí, je mlčet.
    """
    for r in rozmery:
        vyl = pravidla.get(r.jmeno)
        if not vyl:
            continue
        z = r.znacka(a, b)
        if z == vyl:
            return {"druh": "vylouceno", "rozmer": r.jmeno, "znacka": z}
    return {"druh": "nevim"}
