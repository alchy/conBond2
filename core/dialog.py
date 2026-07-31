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
    Kde se narodil Hrabal?          otázka na OBSAH korpusu

DVA DRUHY OTÁZEK. „Je Krakatit dílo?" se ptá na VZTAH a odpovídá znalost.
„Kde se narodil Hrabal?" se ptá na OBSAH a odpovídá pole — vrátí kandidáty,
ne jednu odpověď, protože šablona je abstrakce, která má kandidáty matchnout;
vybrat z nich je jiná úloha.

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

from .tvrzeni import (INSTANCE, PODTRIDA, SYNONYMUM, ZAPOR, Dotaz,
                      Mluvnice, Nejasnost, Tvrzeni, Znalost)

# Druhy záznamu — co se s poslaným textem stalo.
TVRZENI, OTAZKA, RODOKMEN, NEJASNOST, ODMITNUTO, CHYBA, OBSAH = (
    "tvrzeni", "otazka", "rodokmen", "nejasnost", "odmitnuto", "chyba", "obsah")

ZNAK = {PODTRIDA: "⊂", INSTANCE: "∈", SYNONYMUM: "=", ZAPOR: "≠"}

# Jak rychle téma chladne. Po třech tazích na jiné téma zbude z entity
# desetina, po pěti nic — tedy „o čem byla řeč" drží pár tahů, ne celý
# rozhovor. Převzato z ActivationField v conBondu, ale jen ta část, která
# udržuje řetěz; šíření tepla po hranách se sem nepřenáší, protože pole
# ROZŠIŘUJE a my ho potřebujeme zúžit.
CHLADNUTI = 0.55
STUDENE = 0.15


@dataclass
class Zaznam:
    """Jeden tah rozhovoru. Drží i to, co se NEstalo — odmítnutí a nejasnost
    jsou taky výsledek a v přepisu mají být vidět."""
    text: str
    druh: str
    odpoved: str
    hrana: Optional[dict] = None      # {druh, levy, pravy, znak}
    volby: tuple = ()                 # co může člověk rozhodnout
    nalez: Optional[dict] = None      # aktivace a kandidáti u otázky na obsah
    cas: float = field(default_factory=time.time)

    def do_slovniku(self) -> dict:
        return {"text": self.text, "druh": self.druh, "odpoved": self.odpoved,
                "hrana": self.hrana, "volby": list(self.volby),
                "nalez": self.nalez, "cas": self.cas}


class Rozhovor:
    def __init__(self, znalost: Znalost, mluvnice: Optional[Mluvnice] = None,
                 odpovidac=None):
        self.znalost = znalost
        self.mluvnice = mluvnice or Mluvnice()
        self.odpovidac = odpovidac
        self.historie: list[Zaznam] = []
        self.nejasne: Optional[Nejasnost] = None
        self.posledni_nalez: Optional[dict] = None
        self.tema: dict = {}          # entita → teplo

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
        # Otázka na OBSAH se pozná tázacím tvarem a jde do pole, ne do
        # znalosti — „Kde se narodil Hrabal?" žádný vztah nezakládá.
        if self.odpovidac is not None and self.odpovidac.je_na_obsah(text):
            return self.zapsat(self.z_pole(text))
        return self.zapsat(self.prijmout(text))

    def z_pole(self, text: str) -> Zaznam:
        """Odpověď z korpusu. Vrací KANDIDÁTY, ne jedno slovo: šablona je
        abstrakce, která má kandidáty matchnout, ne mezi nimi vybrat."""
        v = self.odpovidac.odpovedet(text, tema=self.horka_temata())
        self.zahrat(v["aktivace"].get("entita"))
        v["kandidati"] = self.z_dialogu(text, v) + v["kandidati"]
        if v["kandidati"]:
            v["odpoved"] = v["kandidati"][0]["text"]
        self.posledni_nalez = v
        a = v["aktivace"]
        kde = f"Ent={a['entita']} ({a['vet_entity']} vět)" if a["entita"] else "bez osoby"
        tvary = ", ".join(f"{t} ({n})" for t, n in a["svitici"].items() if n)
        if v.get("nejasne"):
            kdo = " · ".join(k.replace("_", " ").title() for k in v["nejasne"])
            return Zaznam(text, OBSAH,
                          f"upřesni prosím, koho myslíš: {kdo}", nalez=v)
        if a.get("cizi_jmeno"):
            return Zaznam(text, OBSAH,
                          f"o „{' '.join(a['jmena'])}\" korpus nic neví — "
                          "radši mlčím, než abych odpověděl o někom jiném",
                          nalez=v)
        if not v["kandidati"]:
            popis = f"v poli není nic typu {v['typ']} — {kde}"
            if a["nezname"]:
                popis += f"; nesvítí: {', '.join(a['nezname'])}"
            return Zaznam(text, OBSAH, popis, nalez=v)
        popis = (f"{len(v['kandidati'])} kandidátů z {v['vet']} vět · {kde}"
                 + (f" · {tvary}" if tvary else "")
                 + (" · sloveso nesedlo, beru celou osobu" if a.get("siroko") else "")
                 + (" · pomohla znalost" if v["znalost_pomohla"] else ""))
        return Zaznam(text, OBSAH, popis, nalez=v)

    def prijmout(self, text: str) -> Zaznam:
        vysledek = self.mluvnice.rozeber(text)
        if vysledek is None:
            return Zaznam(text, CHYBA,
                          "tomuhle tvaru nerozumím — zkus „X je druh Y“ "
                          "nebo „? X Y“ pro dotaz")
        # Otázka se NIKDY nesmí zapsat jako tvrzení. „Co je Šmoula?" má tvar
        # „X je Y" a bez tohohle se z tázacího slova stal pojem.
        if isinstance(vysledek, Dotaz):
            if vysledek.cim is None:
                return self.zaradit(vysledek.co, text)
            co, cim = self.rozdelit(vysledek)
            return self.odpovedet_pojmy(co, cim, text)
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
        return self.odpovedet_pojmy(self.mluvnice._pojem(" ".join(kusy[:-1])),
                                    self.mluvnice._pojem(kusy[-1]),
                                    "? " + dotaz.strip())

    def rozdelit(self, dotaz: Dotaz) -> tuple:
        """Kde v „Je Šmoula pohádková bytost?" končí první pojem.

        Mluvnice to rozhodnout nemůže — obě strany smějí být víceslovné.
        Zeptáme se tedy znalosti a vezmeme řez, po kterém obě strany něco
        znamenají; když takový není, aspoň levá; jinak zůstane výchozí."""
        slova = dotaz.slova
        if len(slova) < 2:
            return dotaz.co, dotaz.cim
        nejlepsi, skore = None, -1
        for i in range(1, len(slova)):
            co, cim = " ".join(slova[:i]), " ".join(slova[i:])
            body = 2 * self.znalost.zna(co) + self.znalost.zna(cim)
            if body > skore:
                nejlepsi, skore = (co, cim), body
        return nejlepsi if skore > 0 else (dotaz.co, dotaz.cim)

    def odpovedet_pojmy(self, co: str, cim: str, text: str) -> Zaznam:
        """Pojmy už jsou lemmatizované — sem chodí i česky položená otázka."""
        odpoved = self.znalost.je(co, cim)
        # V odpovědi napsaný tvar, v hraně klíč — počítá se s lemmaty.
        a, b = self.znalost.tvar(co), self.znalost.tvar(cim)
        slovy = {True: f"ano, {a} je {b}",
                 False: f"ne, {a} není {b}",
                 None: "nevím — a mlčení není zápor, jen chybějící znalost"}
        return Zaznam(text, OTAZKA, slovy[odpoved],
                      hrana={"druh": None, "levy": co, "pravy": cim,
                             "znak": {True: "∈", False: "≠", None: "?"}[odpoved]})

    def rodokmen(self, pojem: str) -> Zaznam:
        return self.zaradit(self.mluvnice._pojem(pojem), "?? " + pojem.strip())

    def zaradit(self, pojem: str, text: str) -> Zaznam:
        """Čím vším pojem je. Odpověď na „co je X?" i na „?? X"."""
        predci = sorted(self.znalost.predci(pojem))
        if not predci:
            return Zaznam(text, RODOKMEN,
                          f"o „{self.znalost.tvar(pojem)}“ zatím nic nevím")
        return Zaznam(text, RODOKMEN, f"{self.znalost.tvar(pojem)} ⊂ "
                      + ", ".join(self.znalost.tvar(p) for p in predci))

    # ---- téma --------------------------------------------------------
    def zahrat(self, entita: Optional[str]) -> None:
        """Odpověď zpětně přihřeje to, o čem byla — tím řetěz drží téma.

        Chladne VŠECHNO včetně právě zahřáté entity; jinak by první téma
        rozhovoru zůstalo nejteplejší napořád."""
        for k in list(self.tema):
            self.tema[k] *= CHLADNUTI
            if self.tema[k] < STUDENE:
                del self.tema[k]
        if entita:
            # NASTAVÍ se na plné teplo, NEPŘIČTE. Sčítání znamenalo, že
            # dlouho probírané téma nejde přebít: po šesti tazích o Hrabalovi
            # a jednom o Čapkovi zůstal Hrabal teplejší a „Kde se narodil?"
            # odpovědělo Židenice. Zmínka je přepnutí tématu, ne hlas.
            self.tema[entita] = 1.0

    def horka_temata(self) -> list:
        """Entity od nejteplejší. Otázka bez jména si vezme první."""
        return [k for k, _ in sorted(self.tema.items(), key=lambda x: -x[1])]

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
        # Zobrazuje se napsaný tvar, počítá se s lemmatem — proto obojí.
        hrany = [{"druh": t.druh, "levy": t.levy_tvar, "pravy": t.pravy_tvar,
                  "klic": [t.levy, t.pravy],
                  "znak": ZNAK[t.druh], "zdroj": t.zdroj, "veta": t.veta}
                 for t in self.znalost.tvrzeni]
        # Pojmy jdou z KLÍČŮ, ne ze zobrazených tvarů — jinak by se týž
        # uzel objevil dvakrát, pokaždé v jiném pádu.
        pojmy = sorted({k for h in hrany for k in h["klic"]})
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
                "nalez": self.posledni_nalez,
                "tema": [{"entita": k, "teplo": round(v, 2)}
                         for k, v in sorted(self.tema.items(),
                                            key=lambda x: -x[1])],
                "ceka": self.ceka_na_rozhodnuti()}

    def zapomenout(self) -> None:
        """Zahodí, co se rozhovorem naučilo. Podklad ze svazu zůstane — ten
        se nezadával tady, tak se tu ani nemaže; o návrat k němu se stará
        Znalost, protože hrany z dialogu už v ní leží promíchané s ním."""
        self.historie.clear()
        self.nejasne = None
        self.posledni_nalez = None
        self.tema.clear()
        self.znalost.vycistit()
