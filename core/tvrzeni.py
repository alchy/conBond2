"""Úzká mluvnice tvrzení — znalost se zadává větou, ne tabulkou.

Ne porozumění volnému textu. Pár tvarů, které se píšou skoro česky, ale
čtou se jednoznačně:

    román je druh díla              podtřída
    Krakatit je román               instance
    kompatibilita = slučitelnost    synonymum
    Krakatit není báseň             zápor

Každé přijaté tvrzení je OBJEKT se zdrojem, časem a jistotou — týž tvar
jako návěska od agenta, jen zdrojem je člověk. Tím se chování systému mění
natrvalo a ten dojem učení není klam: systém se opravdu mění.

ČTYŘI DRUHY, PROTOŽE SPLÉST JE ZNAMENÁ NESMYSL. Všechny čtyři jsou v češtině
„X je Y", ale chovají se úplně jinak:

  podtřída  expanduje se nahoru — otázka na dílo trefí román
  instance  neexpanduje, je to konkrétní věc, ne třída
  synonymum oba pojmy splynou v jeden uzel
  zápor     viz níž

Kdyby se instance četla jako podtřída, z „Karel Čapek je člověk" a „člověk
je savec" vyjde, že Čapek je DRUH savce — a začne se chovat jako třída.

ZÁPOR JE JINÝ DRUH OBJEKTU. Pole je monotónní: aktivace říká, co JE. Že něco
NENÍ, v něm vyjádřit nejde a chybějící aktivace znamená „nevíme", ne „ne".
Zápory se proto drží zvlášť a čtou se až při odpovídání, ne při stavbě pole.

KDYŽ SI MLUVNICE NENÍ JISTÁ, ZEPTÁ SE. „pes je savec" může být podtřída
i instance a hádat je horší než se zeptat — špatná hrana se šíří dál
expanzí.
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional

PODTRIDA, INSTANCE, SYNONYMUM, ZAPOR = "podtrida", "instance", "synonymum", "zapor"

# Zkratka psaná s tečkami je JEDEN pojem, ne tři. Tokenizér ji rozseká na
# „r u r" a z Čapkova dramatu se stane nesmysl; tečky proto padnou dřív, než
# se text pošle na lemmatizaci. Dvě a víc písmen s tečkou — „tzv." tedy
# nechytí, což je správně, to zkratka pojmu není.
ZKRATKA = re.compile(r"(?<![\w.])(?:\w\.){2,}")


def sceli_zkratky(text: str) -> str:
    """R.U.R. → RUR, s.r.o. → sro"""
    return ZKRATKA.sub(lambda m: m.group(0).replace(".", ""), text)

# Tvary, které druh určují samy. Cokoli jiného je nejasné a ptáme se.
ZNACKY_PODTRIDY = ("je druh", "je druhem", "patří mezi", "je typ", "je typem")
ZNACKY_SYNONYMA = ("je totéž co", "je totez co", "znamená totéž co", "=",
                   "je synonymum pro", "je jiné slovo pro")

# OTÁZKA NENÍ TVRZENÍ. „Co je Šmoula?" má tvar „X je Y" a bez tohohle se
# zapsalo jako fakt, že co je šmoula — tázací slovo se stalo pojmem. Otázku
# pozná otazník na konci nebo tázací slovo na začátku; obojí, protože
# „kdo je Šmoula" bez otazníku je pořád otázka.
TAZACI = ("co", "kdo", "koho", "komu", "čí", "jaký", "jaká", "jaké", "který",
          "která", "které", "je", "jsou", "není", "nejsou")
# Tázací slova, po kterých se ptáme na ZAŘAZENÍ, ne na jednu hranu.
NA_ZARAZENI = ("co", "kdo", "koho", "komu", "čí")


@dataclass
class Tvrzeni:
    """`levy` a `pravy` jsou LEMMATA — podle nich se pojmy potkávají.
    `levy_tvar` a `pravy_tvar` je to, co člověk napsal, a slouží jen k
    zobrazení: víceslovný pojem se lemmatizuje po slovech, takže
    „pohádková bytost" vyjde jako „pohádkový bytost". Jako klíč je to
    v pořádku a shoda funguje, ale ukazovat se to člověku nemá."""
    druh: str
    levy: str
    pravy: str
    zdroj: str = "dialog"
    cas: float = field(default_factory=time.time)
    jistota: float = 1.0
    veta: str = ""
    levy_tvar: str = ""
    pravy_tvar: str = ""

    def __post_init__(self) -> None:
        self.levy_tvar = self.levy_tvar or self.levy
        self.pravy_tvar = self.pravy_tvar or self.pravy

    def znak(self) -> str:
        return {PODTRIDA: "⊂", INSTANCE: "∈", SYNONYMUM: "=", ZAPOR: "≠"}[self.druh]

    def do_slovniku(self) -> dict:
        return {"druh": self.druh, "levy": self.levy, "pravy": self.pravy,
                "zdroj": self.zdroj, "cas": self.cas,
                "jistota": self.jistota, "veta": self.veta,
                "levy_tvar": self.levy_tvar, "pravy_tvar": self.pravy_tvar}

    @classmethod
    def ze_slovniku(cls, d: dict) -> "Tvrzeni":
        return cls(**{k: d[k] for k in
                      ("druh", "levy", "pravy", "zdroj", "cas", "jistota",
                       "veta", "levy_tvar", "pravy_tvar")
                      if k in d})

    def __str__(self) -> str:
        return f"{self.levy_tvar} {self.znak()} {self.pravy_tvar}"


@dataclass
class Dotaz:
    """Otázka položená česky, ne přes „?". `cim` je None u „co je X?" — tam
    se ptáme na zařazení, ne na jednu hranu.

    `slova` nese lemmata nerozdělená, protože „Je Šmoula pohádková bytost?"
    natvrdo rozdělit nejde: podle posledního slova vyjde „Šmoula pohádková"
    a „bytost". Kde je řez, ví až znalost, a ta sem nepatří."""
    co: str
    cim: Optional[str] = None
    veta: str = ""
    slova: tuple = ()


@dataclass
class Nejasnost:
    """Mluvnice tvar rozpoznala, ale neví, jestli je to podtřída, nebo
    instance. Nehádá — vrací otázku."""
    levy: str
    pravy: str
    veta: str
    levy_tvar: str = ""
    pravy_tvar: str = ""

    def otazka(self) -> str:
        l, p = self.levy_tvar or self.levy, self.pravy_tvar or self.pravy
        return (f"Je „{l}\" DRUH pojmu „{p}\" (jako román je druh "
                f"díla), nebo KONKRÉTNÍ {p} (jako Krakatit je román)?")

    def rozhodni(self, druh: str) -> Tvrzeni:
        return Tvrzeni(druh=druh, levy=self.levy, pravy=self.pravy,
                       veta=self.veta, levy_tvar=self.levy_tvar,
                       pravy_tvar=self.pravy_tvar)


class Mluvnice:
    """Věta → tvrzení. Lemmatizaci obstará předaná funkce (u nás UDPipe),
    protože „román je druh díla" má pravou stranu v genitivu a bez lemmat
    by z toho byl jiný uzel než „dílo"."""

    def __init__(self, lemmatizuj=None):
        self.lemmatizuj = lemmatizuj or (lambda s: s.strip().lower())

    def rozeber(self, veta: str):
        """Vrací Tvrzeni, Dotaz, Nejasnost, nebo None. Otázka se testuje
        PRVNÍ: „Co je Šmoula?" má tvar tvrzení a jinak by se zapsala jako
        fakt, že co je šmoula."""
        syrova = sceli_zkratky(veta.strip())
        cista = syrova.rstrip(".!?")
        if not cista:
            return None
        if syrova.endswith("?") or self._prvni_slovo(cista) in TAZACI:
            return self._dotaz(cista, veta)

        for znacka in ZNACKY_SYNONYMA:
            if znacka in cista.lower():
                l, p = self._rozdel(cista, znacka)
                return self._tvrzeni(SYNONYMUM, l, p, veta)

        if self._obsahuje(cista, " není "):
            l, p = self._rozdel(cista, " není ")
            return self._tvrzeni(ZAPOR, l, p, veta)

        for znacka in ZNACKY_PODTRIDY:
            if znacka in cista.lower():
                l, p = self._rozdel(cista, znacka)
                return self._tvrzeni(PODTRIDA, l, p, veta)

        if self._obsahuje(cista, " je "):
            l, p = self._rozdel(cista, " je ")
            levy_syrovy = l.strip()
            # Velké písmeno = konkrétní věc. V češtině je to slušné vodítko
            # u vlastních jmen; kde nestačí, ptáme se.
            #
            # Celá verzálka se dřív vylučovala, aby se za jméno nepovažoval
            # křik. Jenže tím propadly zkratky: R.U.R. se scelí na „RUR"
            # a to je vlastní jméno jako každé jiné.
            if levy_syrovy[:1].isupper():
                return self._tvrzeni(INSTANCE, l, p, veta)
            return Nejasnost(self._pojem(l), self._pojem(p), veta,
                             self._ocistit(l), self._ocistit(p))
        return None

    def _tvrzeni(self, druh: str, l: str, p: str, veta: str) -> "Tvrzeni":
        """Lemma jako klíč, napsaný tvar k zobrazení."""
        return Tvrzeni(druh, self._pojem(l), self._pojem(p), veta=veta,
                       levy_tvar=self._ocistit(l), pravy_tvar=self._ocistit(p))

    @staticmethod
    def _ocistit(kus: str) -> str:
        """Povrchový tvar bez značek — lemmatizace se sem nesahá."""
        kus = sceli_zkratky(kus.strip()).strip(",;")
        for predlozka in ("pro ", "s ", "se ", "co "):
            if kus.lower().startswith(predlozka):
                kus = kus[len(predlozka):]
        return kus.strip()

    @staticmethod
    def _prvni_slovo(veta: str) -> str:
        kusy = veta.strip().split()
        return kusy[0].lower().strip(",;") if kusy else ""

    @staticmethod
    def _obsahuje(veta: str, znacka: str) -> bool:
        """Hledá se v ODSAZENÉM řetězci, aby značka chytla i na kraji věty."""
        return znacka.lower() in f" {veta.lower()} "

    @staticmethod
    def _rozdel(veta: str, znacka: str):
        """Dělí se v témž odsazeném řetězci, ve kterém se hledalo.

        Dřív se hledalo v odsazeném a dělilo v neodsazeném, takže věta
        začínající značkou („je Šmoula skřítek") test prošla a na dělení
        spadla — ValueError až ven z API jako pětistovka."""
        odsazena = f" {veta} "
        i = odsazena.lower().find(znacka.lower())
        if i < 0:
            return veta, ""
        return odsazena[:i].strip(), odsazena[i + len(znacka):].strip()

    def _dotaz(self, cista: str, veta: str):
        """Česky položená otázka. Konvence je táž jako u „? X Y": poslední
        slovo je to, na co se ptáme, zbytek je pojem — víceslovné pojmy na
        obou stranách naráz rozdělit nejde."""
        prvni = self._prvni_slovo(cista)
        if prvni in NA_ZARAZENI and self._obsahuje(cista, " je "):
            _, pojem = self._rozdel(cista, " je ")
            return Dotaz(self._pojem(pojem), None, veta) if pojem else None
        if prvni in ("je", "jsou", "není", "nejsou"):
            zbytek = cista.split(None, 1)[1] if len(cista.split(None, 1)) > 1 else ""
            kusy = zbytek.split()
            if len(kusy) >= 2:
                slova = tuple(self._pojem(k) for k in kusy)
                # výchozí řez u posledního slova; lepší najde až znalost
                return Dotaz(" ".join(slova[:-1]), slova[-1], veta, slova)
            return None
        if self._obsahuje(cista, " je "):
            l, p = self._rozdel(cista, " je ")
            if l and p:
                return Dotaz(self._pojem(l), self._pojem(p), veta)
        return None

    def _pojem(self, kus: str) -> str:
        # Scelení i tady, ne jen v rozeber(): dotazy „? R.U.R. dílo" jdou
        # rovnou sem a jinak by se ptaly na jiný uzel, než jaký se uložil.
        kus = sceli_zkratky(kus.strip()).strip(",;")
        for predlozka in ("pro ", "s ", "se ", "co "):
            if kus.lower().startswith(predlozka):
                kus = kus[len(predlozka):]
        return self.lemmatizuj(kus)


class Znalost:
    """Přijatá tvrzení a odvozování nad nimi.

    Svaz z Wikidat se sem načte jako podklad; tvrzení z dialogu ho doplňují
    a opravují. Zdroj se u každé hrany drží, takže jde poznat, co odkud je.
    """

    def __init__(self, soubor: Optional[str] = None):
        self.soubor = soubor
        self.svaz: Optional[str] = None   # odkud přišel podklad, kvůli úklidu
        self.tvrzeni: list = []
        self.nadrazene: dict = {}       # pojem → [nadřazené]
        self.synonyma: dict = {}        # pojem → zástupce
        self.zapory: set = set()
        # lemma → jak to člověk napsal. Kvůli odpovědím: uzel „pohádkový
        # bytost" je správný klíč, ale říct se má „pohádková bytost".
        self.tvary: dict = {}
        if soubor and os.path.exists(soubor):
            self.nacti()

    # ---- příjem ------------------------------------------------------
    def prijmi(self, t: Tvrzeni) -> Optional[str]:
        """Vrací None při přijetí, jinak důvod odmítnutí."""
        self.tvary.setdefault(t.levy, t.levy_tvar)
        self.tvary.setdefault(t.pravy, t.pravy_tvar)
        l, p = self.zastupce(t.levy), self.zastupce(t.pravy)
        if l == p and t.druh != SYNONYMUM:
            return f"„{t.levy}\" a „{t.pravy}\" už jsou totéž"
        if t.druh == PODTRIDA:
            if p in self.predci(l) or l in self.predci(p):
                if l in self.predci(p):
                    return (f"to by byl kruh: „{t.pravy}\" už je pod "
                            f"„{t.levy}\"")
            self.nadrazene.setdefault(l, [])
            if p not in self.nadrazene[l]:
                self.nadrazene[l].append(p)
        elif t.druh == INSTANCE:
            self.nadrazene.setdefault(l, [])
            if p not in self.nadrazene[l]:
                self.nadrazene[l].append(p)
        elif t.druh == SYNONYMUM:
            self.synonyma[l] = p
        elif t.druh == ZAPOR:
            if p in self.predci(l):
                return (f"odporuje si to: „{t.levy}\" už je „{t.pravy}\"")
            self.zapory.add((l, p))
        self.tvrzeni.append(t)
        return None

    # ---- odvozování --------------------------------------------------
    def tvar(self, pojem: str) -> str:
        """Jak se pojem napsal, když o něm poprvé padlo slovo."""
        return self.tvary.get(pojem, pojem)

    def zna(self, pojem: str) -> bool:
        """Padlo o tomhle pojmu vůbec někdy slovo? Slouží k rozřezání
        otázky, ne k odpovídání — neznalost pojmu není zápor."""
        p = self.zastupce(pojem)
        if p in self.nadrazene or p in self.synonyma:
            return True
        if any(p == c for dvojice in self.zapory for c in dvojice):
            return True
        return any(p == rodic for rodice in self.nadrazene.values()
                   for rodic in rodice)

    def zastupce(self, pojem: str) -> str:
        """Synonyma splývají v jeden uzel; tohle je jeho jméno."""
        videno = set()
        while pojem in self.synonyma and pojem not in videno:
            videno.add(pojem)
            pojem = self.synonyma[pojem]
        return pojem

    def predci(self, pojem: str, hloubka: int = 12) -> set:
        """Všechno, čím pojem tranzitivně je. TOHLE je ta expanze."""
        out, fronta = set(), [(self.zastupce(pojem), 0)]
        while fronta:
            p, h = fronta.pop()
            if h >= hloubka:
                continue
            for rodic in self.nadrazene.get(p, []):
                r = self.zastupce(rodic)
                if r in out:
                    continue
                out.add(r)
                fronta.append((r, h + 1))
        return out

    def je(self, co: str, cim: str) -> Optional[bool]:
        """True / False / None, kde None znamená POCTIVĚ „nevím".

        Chybějící hrana není zápor — pole je monotónní a mlčení neznamená
        popření. Proto tři hodnoty, ne dvě."""
        c, k = self.zastupce(co), self.zastupce(cim)
        if c == k or k in self.predci(c):
            return True
        if (c, k) in self.zapory:
            return False
        for pred in self.predci(c):
            if (pred, k) in self.zapory:
                return False
        return None

    # ---- podklad a uložení -------------------------------------------
    def naplnit_ze_svazu(self, cesta: str) -> int:
        """Svaz z Wikidat jako podklad. Hrany dostanou zdroj `wikidata`,
        aby šlo poznat, co je odkud."""
        self.svaz = cesta
        if not os.path.exists(cesta):
            return 0
        d = json.load(open(cesta, encoding="utf-8"))
        uzly, kolik = d["uzly"], 0
        for qid, rodice in d["nadrazene"].items():
            l = uzly.get(qid, "").lower()
            if not l:
                continue
            for r in rodice:
                p = uzly.get(r, "").lower()
                if not p or p == l:
                    continue
                self.nadrazene.setdefault(l, [])
                if p not in self.nadrazene[l]:
                    self.nadrazene[l].append(p)
                    kolik += 1
        return kolik

    def vycistit(self) -> None:
        """Zapomene, co se přidalo dialogem, a vrátí se k holému podkladu.

        Nestačí smazat seznam tvrzení: hrany z nich už sedí v `nadrazene`
        vedle hran ze svazu a rozeznat je tam po sobě nejde. Proto se vyklidí
        všechno a podklad se natáhne znovu — proto si taky Znalost pamatuje,
        odkud přišel."""
        self.tvrzeni.clear()
        self.nadrazene.clear()
        self.synonyma.clear()
        self.zapory.clear()
        self.tvary.clear()
        if self.svaz:
            self.naplnit_ze_svazu(self.svaz)
        self.uloz()

    def uloz(self) -> None:
        if not self.soubor:
            return
        os.makedirs(os.path.dirname(self.soubor), exist_ok=True)
        json.dump({"tvrzeni": [t.do_slovniku() for t in self.tvrzeni]},
                  open(self.soubor, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    def nacti(self) -> None:
        d = json.load(open(self.soubor, encoding="utf-8"))
        for zaznam in d.get("tvrzeni", []):
            self.prijmi(Tvrzeni.ze_slovniku(zaznam))
