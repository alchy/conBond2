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


@dataclass
class Tvrzeni:
    druh: str
    levy: str
    pravy: str
    zdroj: str = "dialog"
    cas: float = field(default_factory=time.time)
    jistota: float = 1.0
    veta: str = ""

    def do_slovniku(self) -> dict:
        return {"druh": self.druh, "levy": self.levy, "pravy": self.pravy,
                "zdroj": self.zdroj, "cas": self.cas,
                "jistota": self.jistota, "veta": self.veta}

    @classmethod
    def ze_slovniku(cls, d: dict) -> "Tvrzeni":
        return cls(**{k: d[k] for k in
                      ("druh", "levy", "pravy", "zdroj", "cas", "jistota", "veta")
                      if k in d})

    def __str__(self) -> str:
        znak = {PODTRIDA: "⊂", INSTANCE: "∈", SYNONYMUM: "=", ZAPOR: "≠"}[self.druh]
        return f"{self.levy} {znak} {self.pravy}"


@dataclass
class Nejasnost:
    """Mluvnice tvar rozpoznala, ale neví, jestli je to podtřída, nebo
    instance. Nehádá — vrací otázku."""
    levy: str
    pravy: str
    veta: str

    def otazka(self) -> str:
        return (f"Je „{self.levy}\" DRUH pojmu „{self.pravy}\" (jako román je druh "
                f"díla), nebo KONKRÉTNÍ {self.pravy} (jako Krakatit je román)?")

    def rozhodni(self, druh: str) -> Tvrzeni:
        return Tvrzeni(druh=druh, levy=self.levy, pravy=self.pravy, veta=self.veta)


class Mluvnice:
    """Věta → tvrzení. Lemmatizaci obstará předaná funkce (u nás UDPipe),
    protože „román je druh díla" má pravou stranu v genitivu a bez lemmat
    by z toho byl jiný uzel než „dílo"."""

    def __init__(self, lemmatizuj=None):
        self.lemmatizuj = lemmatizuj or (lambda s: s.strip().lower())

    def rozeber(self, veta: str):
        cista = sceli_zkratky(veta.strip()).rstrip(".!?")
        if not cista:
            return None

        for znacka in ZNACKY_SYNONYMA:
            if znacka in cista.lower():
                l, p = self._rozdel(cista, znacka)
                return Tvrzeni(SYNONYMUM, self._pojem(l), self._pojem(p), veta=veta)

        if " není " in f" {cista} " or cista.lower().startswith("není "):
            l, p = self._rozdel(cista, " není ")
            return Tvrzeni(ZAPOR, self._pojem(l), self._pojem(p), veta=veta)

        for znacka in ZNACKY_PODTRIDY:
            if znacka in cista.lower():
                l, p = self._rozdel(cista, znacka)
                return Tvrzeni(PODTRIDA, self._pojem(l), self._pojem(p), veta=veta)

        if " je " in f" {cista} ":
            l, p = self._rozdel(cista, " je ")
            levy_syrovy = l.strip()
            # Velké písmeno = konkrétní věc. V češtině je to slušné vodítko
            # u vlastních jmen; kde nestačí, ptáme se.
            #
            # Celá verzálka se dřív vylučovala, aby se za jméno nepovažoval
            # křik. Jenže tím propadly zkratky: R.U.R. se scelí na „RUR"
            # a to je vlastní jméno jako každé jiné.
            if levy_syrovy[:1].isupper():
                return Tvrzeni(INSTANCE, self._pojem(l), self._pojem(p), veta=veta)
            return Nejasnost(self._pojem(l), self._pojem(p), veta)
        return None

    @staticmethod
    def _rozdel(veta: str, znacka: str):
        i = veta.lower().index(znacka.lower())
        return veta[:i], veta[i + len(znacka):]

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
        self.tvrzeni: list = []
        self.nadrazene: dict = {}       # pojem → [nadřazené]
        self.synonyma: dict = {}        # pojem → zástupce
        self.zapory: set = set()
        if soubor and os.path.exists(soubor):
            self.nacti()

    # ---- příjem ------------------------------------------------------
    def prijmi(self, t: Tvrzeni) -> Optional[str]:
        """Vrací None při přijetí, jinak důvod odmítnutí."""
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
