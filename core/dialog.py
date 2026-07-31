"""Rozhovor jako objekt: věta dovnitř, záznam ven.

Tohle je jádro listu Dialog. Prohlížeč nerozhoduje o ničem — pošle text a
dostane zpátky, co se s ním stalo. Táž třída obslouží i REPL v terminálu,
protože zdroj pravdy sedí tady, ne v jednom ze dvou kanálů.

CO ROZHOVOR UMÍ

    román je druh díla              podtřída
    Krakatit je román               instance
    kompatibilita = slučitelnost    synonymum
    Krakatit není báseň             zápor
    ? Krakatit dílo                 dotaz  → ano / ne / nevím
    ?? Krakatit                     rodokmen — čím vším to je

TŘI ODPOVĚDI, NE DVĚ. `nevím` není výmluva: pole je monotónní a chybějící
hrana znamená, že se nikdo neptal, ne že odpověď je ne. Proto se `ne` řekne
jen tam, kde je zápor doopravdy zapsaný.

KDYŽ SI MLUVNICE NENÍ JISTÁ, ROZHOVOR SE ZASEKNE a čeká na rozhodnutí.
„pes je savec" může být podtřída i instance a špatná hrana se šíří expanzí
dál, takže hádat je horší než se zeptat.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from .tvrzeni import (INSTANCE, PODTRIDA, SYNONYMUM, ZAPOR, Mluvnice,
                      Nejasnost, Tvrzeni, Znalost)

# Druhy záznamu — co se s poslaným textem stalo.
TVRZENI, OTAZKA, RODOKMEN, NEJASNOST, ODMITNUTO, CHYBA = (
    "tvrzeni", "otazka", "rodokmen", "nejasnost", "odmitnuto", "chyba")

ZNAK = {PODTRIDA: "⊂", INSTANCE: "∈", SYNONYMUM: "=", ZAPOR: "≠"}


@dataclass
class Zaznam:
    """Jeden tah rozhovoru. Drží i to, co se NEstalo — odmítnutí a nejasnost
    jsou taky výsledek a v přepisu mají být vidět."""
    text: str
    druh: str
    odpoved: str
    hrana: Optional[dict] = None      # {druh, levy, pravy, znak}
    volby: tuple = ()                 # co může člověk rozhodnout
    cas: float = field(default_factory=time.time)

    def do_slovniku(self) -> dict:
        return {"text": self.text, "druh": self.druh, "odpoved": self.odpoved,
                "hrana": self.hrana, "volby": list(self.volby), "cas": self.cas}


class Rozhovor:
    def __init__(self, znalost: Znalost, mluvnice: Optional[Mluvnice] = None):
        self.znalost = znalost
        self.mluvnice = mluvnice or Mluvnice()
        self.historie: list[Zaznam] = []
        self.nejasne: Optional[Nejasnost] = None

    # ---- příjem ------------------------------------------------------
    def poslat(self, text: str) -> Zaznam:
        """Jeden řádek od člověka. Rozhovor, který čeká na rozhodnutí, další
        větu nepřijme — jinak by se nedořešená hrana ztratila."""
        text = (text or "").strip()
        if not text:
            return self.zapsat(Zaznam(text, CHYBA, "prázdný vstup"))
        if self.nejasne is not None:
            return self.zapsat(Zaznam(
                text, NEJASNOST, "nejdřív rozhodni předchozí větu",
                volby=(PODTRIDA, INSTANCE)))
        if text.startswith("??"):
            return self.zapsat(self.rodokmen(text[2:]))
        if text.startswith("?"):
            return self.zapsat(self.odpovedet(text[1:]))
        return self.zapsat(self.prijmout(text))

    def prijmout(self, text: str) -> Zaznam:
        vysledek = self.mluvnice.rozeber(text)
        if vysledek is None:
            return Zaznam(text, CHYBA,
                          "tomuhle tvaru nerozumím — zkus „X je druh Y“ "
                          "nebo „? X Y“ pro dotaz")
        if isinstance(vysledek, Nejasnost):
            self.nejasne = vysledek
            return Zaznam(text, NEJASNOST, vysledek.otazka(),
                          hrana={"druh": None, "levy": vysledek.levy,
                                 "pravy": vysledek.pravy, "znak": "?"},
                          volby=(PODTRIDA, INSTANCE))
        return self.zapsat_tvrzeni(text, vysledek)

    def rozhodnout(self, druh: str) -> Zaznam:
        """Odpověď na nejasnost. Bez čekající nejasnosti se nedá rozhodovat."""
        if self.nejasne is None:
            return self.zapsat(Zaznam("", CHYBA, "není co rozhodovat"))
        if druh not in (PODTRIDA, INSTANCE):
            return self.zapsat(Zaznam("", CHYBA, f"neznámý druh {druh!r}"))
        nejasne, self.nejasne = self.nejasne, None
        return self.zapsat(self.zapsat_tvrzeni(nejasne.veta, nejasne.rozhodni(druh)))

    def preskocit(self) -> Zaznam:
        nejasne, self.nejasne = self.nejasne, None
        text = nejasne.veta if nejasne else ""
        return self.zapsat(Zaznam(text, ODMITNUTO, "přeskočeno"))

    def zapsat_tvrzeni(self, text: str, t: Tvrzeni) -> Zaznam:
        chyba = self.znalost.prijmi(t)
        hrana = {"druh": t.druh, "levy": t.levy, "pravy": t.pravy,
                 "znak": ZNAK[t.druh]}
        if chyba:
            return Zaznam(text, ODMITNUTO, chyba, hrana=hrana)
        self.znalost.uloz()
        return Zaznam(text, TVRZENI, f"přijato: {t}", hrana=hrana)

    # ---- dotazy ------------------------------------------------------
    def odpovedet(self, dotaz: str) -> Zaznam:
        kusy = dotaz.split()
        if len(kusy) < 2:
            return Zaznam("?" + dotaz, CHYBA, "ptej se ve tvaru: ? Krakatit dílo")
        co = self.mluvnice._pojem(" ".join(kusy[:-1]))
        cim = self.mluvnice._pojem(kusy[-1])
        odpoved = self.znalost.je(co, cim)
        slovy = {True: f"ano, {co} je {cim}",
                 False: f"ne, {co} není {cim}",
                 None: "nevím — a mlčení není zápor, jen chybějící znalost"}
        return Zaznam("? " + dotaz.strip(), OTAZKA, slovy[odpoved],
                      hrana={"druh": None, "levy": co, "pravy": cim,
                             "znak": {True: "∈", False: "≠", None: "?"}[odpoved]})

    def rodokmen(self, pojem: str) -> Zaznam:
        p = self.mluvnice._pojem(pojem)
        predci = sorted(self.znalost.predci(p))
        if not predci:
            return Zaznam("?? " + pojem.strip(), RODOKMEN,
                          f"o „{p}“ zatím nic nevím")
        return Zaznam("?? " + pojem.strip(), RODOKMEN,
                      f"{p} ⊂ " + ", ".join(predci))

    # ---- čtení -------------------------------------------------------
    def zapsat(self, zaznam: Zaznam) -> Zaznam:
        self.historie.append(zaznam)
        return zaznam

    def ceka_na_rozhodnuti(self) -> bool:
        return self.nejasne is not None

    def vypsat_historii(self) -> list:
        return [z.do_slovniku() for z in self.historie]

    def vypsat_znalost(self) -> dict:
        """Znalost k vykreslení: uzly, hrany a čísla.

        Posílají se JEN hrany z dialogu, ne celý svaz z Wikidat — těch je
        skoro sto a v přepisu rozhovoru nemají co dělat. Odvození přes ně
        samozřejmě běží dál, takže „Krakatit je dílo“ vyjde i tehdy, když se
        o díle nikdo nezmínil."""
        hrany = [{"druh": t.druh, "levy": t.levy, "pravy": t.pravy,
                  "znak": ZNAK[t.druh], "zdroj": t.zdroj, "veta": t.veta}
                 for t in self.znalost.tvrzeni]
        pojmy = sorted({k for h in hrany for k in (h["levy"], h["pravy"])})
        return {
            "hrany": hrany,
            "pojmy": [{"jmeno": p, "predci": sorted(self.znalost.predci(p))}
                      for p in pojmy],
            "cisla": {
                "tvrzeni": len(self.znalost.tvrzeni),
                "pojmy": len(pojmy),
                "zapory": len(self.znalost.zapory),
                "synonyma": len(self.znalost.synonyma),
                "uzlu_celkem": len(self.znalost.nadrazene),
            },
        }

    def vypsat_stav(self) -> dict:
        return {"historie": self.vypsat_historii(),
                "znalost": self.vypsat_znalost(),
                "ceka": self.ceka_na_rozhodnuti()}

    def zapomenout(self) -> None:
        """Zahodí, co se rozhovorem naučilo. Podklad ze svazu zůstane — ten
        se nezadával tady, tak se tu ani nemaže; o návrat k němu se stará
        Znalost, protože hrany z dialogu už v ní leží promíchané s ním."""
        self.historie.clear()
        self.nejasne = None
        self.znalost.vycistit()
