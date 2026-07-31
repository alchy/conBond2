"""Příjem textu: syrový článek → korpus. Stavební bloky, ne skript.

Doteď to celé žilo v `scripts/baseline.py` jako funkce. Podle vlastního
pravidla projektu patří zdroj pravdy do knihovny — skript má být tenký
a cizí program má umět totéž bez něj:

    from core.ingest import Prijem
    Prijem(config).vse()

ČTYŘI KROKY, KAŽDÝ SÁM O SOBĚ

    Cistic       syrový text → věty       co do korpusu nepatří
    Rozbor       věty → tokeny            UDPipe, JEDEN klient pro celý projekt
    Vypovedi     próza / seznam           57 % „vět" je bibliografie
    Prijem       fasáda

JEDEN KLIENT UDPIPE, A JE TO PODSTATNÉ. Dřív byly dva — `baseline.rozebrat()`
a `server/parse.Rozbor` — a lišily se v tom, co dělají se zkratkami. Korpus
tedy mohl mít „R.U.R." rozsekané na tři tokeny a otázka scelené, nebo naopak;
obojí by dál „fungovalo" a jen by mluvilo o jiném slově. Lekce z conBondu
(`normalize.py`): oprava tokenizace patří na JEDINÝ chokepoint, kterým projde
korpus i dotaz.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional, Sequence

from .agents import oznacit_korpus
from .config import Config
from .log import log
from .tvrzeni import sceli_zkratky

# Řádky, které do korpusu nepatří: nadpisy sekcí, odkazy, holé seznamy.
NEPATRI = re.compile(r"^\s*(==|\*|#|\|)|^\s*$")
# Věta kratší než tohle je skoro jistě zbytek po čištění, ne věta.
MIN_SLOV = 4


class Cistic:
    """Syrový text článku → řádky, ze kterých má smysl dělat věty."""

    def __init__(self, min_slov: int = MIN_SLOV):
        self.min_slov = min_slov

    def vycistit_radek(self, radek: str) -> str:
        radek = re.sub(r"\[\d+\]", "", radek)      # poznámky pod čarou
        radek = re.sub(r"\s+", " ", radek)
        # Zkratka s tečkami je JEDEN pojem. Scelí se TADY, na vstupu, ať
        # korpus i dotaz vidí totéž — viz normalize.py v conBondu.
        return sceli_zkratky(radek.strip())

    def z_textu(self, text: str) -> list:
        out = []
        for radek in text.splitlines():
            if NEPATRI.match(radek):
                continue
            radek = self.vycistit_radek(radek)
            if len(radek.split()) >= self.min_slov:
                out.append(radek)
        return out

    def ze_souboru(self, cesta: str) -> list:
        with open(cesta, encoding="utf-8") as f:
            return self.z_textu(f.read())

    def ze_slozky(self, slozka: str) -> dict:
        """Článek → jeho řádky. Klíč je jméno souboru bez přípony a slouží
        jako IDENTITA entity — lemma z rozboru by dalo holé „karel"."""
        out = {}
        for jmeno in sorted(os.listdir(slozka)):
            if not jmeno.endswith(".txt"):
                continue
            out[jmeno[:-4]] = self.ze_souboru(os.path.join(slozka, jmeno))
            log.info("článek načten", kdo=jmeno[:-4], radku=len(out[jmeno[:-4]]))
        return out


@dataclass
class Token:
    """Jeden token tak, jak ho pole potřebuje. `lemma` se do korpusu
    nezapisuje — do vektoru patří typ, ne hodnota —, ale během přípravy je
    potřeba (koreference, pojmy)."""
    form: str
    lemma: str
    upos: str
    deprel: str
    feats: Sequence[str]
    id: int = 0
    head: int = 0

    def do_slovniku(self, s_lemmatem: bool = True) -> dict:
        t = {"form": self.form, "upos": self.upos, "id": self.id,
             "head": self.head,
             "acts": [self.upos, self.deprel] + list(self.feats)}
        if s_lemmatem:
            t["lemma"] = self.lemma
        return t


class Rozbor:
    """Klient k vlastní instanci UDPipe. JEDINÝ v projektu.

    Umí jediné: poslat text a vrátit věty tokenů. CoNLL-U ven nepouštíme,
    ať se s ním nemusí zabývat ani prohlížeč, ani příprava korpusu."""

    def __init__(self, url: str, timeout: int = 600):
        self.url = url.rstrip("/") + "/process"
        self.timeout = timeout

    def poslat(self, text: str) -> str:
        telo = urllib.parse.urlencode({
            "tokenizer": "", "tagger": "", "parser": "", "data": text,
        }).encode("utf-8")
        with urllib.request.urlopen(self.url, telo, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8")).get("result", "")

    def rozebrat(self, text: str) -> list:
        """Text → věty tokenů. Text projde týmž scelením zkratek jako
        korpus, protože je to týž chokepoint."""
        return self.z_conllu(self.poslat(sceli_zkratky(text)))

    @staticmethod
    def z_conllu(vysledek: str) -> list:
        vety, tokeny = [], []
        for radek in vysledek.splitlines():
            if radek.startswith(("# newdoc", "# newpar")):
                continue
            if not radek.strip():
                if tokeny:
                    vety.append(tokeny)
                    tokeny = []
                continue
            if radek.startswith("#"):
                continue
            c = radek.split("\t")
            if len(c) < 8 or "-" in c[0] or "." in c[0]:
                continue
            tokeny.append(Token(
                form=c[1], lemma=c[2], upos=c[3], deprel=c[7],
                feats=[] if c[5] == "_" else c[5].split("|"),
                id=int(c[0]), head=int(c[6]) if c[6].isdigit() else 0))
        if tokeny:
            vety.append(tokeny)
        return vety

    def vety_slovniku(self, text: str, s_lemmatem: bool = True) -> list:
        return [[t.do_slovniku(s_lemmatem) for t in v]
                for v in self.rozebrat(text)]

    def lemmata(self, text: str) -> Optional[str]:
        """Jen lemmata, pro pojmy z dialogu. „román je druh díla" má pravou
        stranu v genitivu; bez lemmat by z toho byl jiný uzel než „dílo"."""
        vety = self.rozebrat(text)
        lem = [t.lemma.lower() for v in vety for t in v if t.upos != "PUNCT"]
        return " ".join(lem) or None


class Vypovedi:
    """Próza, nebo položka seznamu?

    Měření: 57 % „vět" v korpusu nemá slovesný kořen a je to bibliografie
    („Praha : Academia , 1985 ."). NEMAŽE SE TO — pole má být obraz textu.
    Označí se a kdo měří výpovědi, si odfiltruje; pro pole je to navíc
    užitečná osa, protože soused v bibliografii je jiné místo než soused ve
    větě. Bez příznaku mělo 6558 šablon (14 %) v sobě obojí."""

    @staticmethod
    def je_proza(veta: Sequence[dict]) -> bool:
        return any("root" in t["acts"] and t["upos"] in ("VERB", "AUX")
                   for t in veta)

    def oznacit(self, vety: Sequence[Sequence[dict]]) -> dict:
        """Na KAŽDÝ token schválně: šablona se skládá ze sousedů, takže
        kdyby to nesl jen kořen, sousedi by o tom nevěděli."""
        pocty = {"proza": 0, "seznam": 0}
        for v in vety:
            druh = "proza" if self.je_proza(v) else "seznam"
            pocty[druh] += 1
            for t in v:
                if f"Vyp={druh}" not in t["acts"]:
                    t["acts"].append(f"Vyp={druh}")
        return pocty


class Prijem:
    """Fasáda: složka se články → korpus vět.

    Koreference tady NENÍ — je to vlastní krok s vlastním měřením a sedí
    v scripts/baseline.py, dokud se neustálí. Sem patří to, co je hotové."""

    def __init__(self, config: Optional[Config] = None,
                 rozbor: Optional[Rozbor] = None):
        self.config = config or Config.nacist()
        self.cistic = Cistic()
        self.rozbor = rozbor or Rozbor(self.config.udpipe)
        self.vypovedi = Vypovedi()

    def nacist(self, slozka: str) -> dict:
        return self.cistic.ze_slozky(slozka)

    def rozebrat(self, clanky: dict, davka: int = 60) -> dict:
        """Věty po dávkách — jedno volání na celý článek je pro UDPipe moc
        a jedno na větu zbytečně pomalé."""
        out = {}
        for kdo, radky in clanky.items():
            vety = []
            for i in range(0, len(radky), davka):
                vety.extend(self.rozbor.vety_slovniku("\n".join(radky[i:i + davka])))
            out[kdo] = vety
            log.info("článek rozebrán", kdo=kdo, vet=len(vety))
        return out

    def slozit(self, clanky: dict) -> list:
        """Články → jeden korpus. Původ věty se drží MIMO `acts`: kdyby se
        dostal do vektoru, rozpadly by se šablony po autorech."""
        vety = []
        for kdo in sorted(clanky):
            for poradi, v in enumerate(clanky[kdo]):
                for t in v:
                    t.pop("lemma", None)
                    t["dok"] = kdo
                    t["vd"] = poradi
                vety.append(v)
        souhrn = oznacit_korpus(vety)
        log.info("agenti označili", **souhrn)
        pocty = self.vypovedi.oznacit(vety)
        log.info("druh výpovědi označen", **pocty)
        return vety
