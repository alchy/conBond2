"""Odvozené vertikály — týž atribut v hrubším rozlišení.

PROČ. Sítko umí říct, co se na kterém offsetu počítá, a měření ukázalo, že
cena slotu závisí na MOHUTNOSTI toho, co se v něm vidí: dohlédnout o slovo
dál stojí 42 bodů sdílení plným pohledem, 33 bodů přes UPOS (17 hodnot) a
14 bodů přes tříhodnotovou třídu. Na to ale musí ta hrubá hodnota existovat —
UPOS je nejhrubší, co UDPipe dodá, a je pořád moc jemné.

CO TO JE. Deklarovaný převod z jemné hodnoty na hrubou. `NOUN` i `VERB` jsou
`Trida=plny`, `ADP` i `AUX` jsou `Trida=pomocny`. Počítá se při čtení, do
korpusu se nic nedopisuje: je to funkce toho, co tam už je.

PROČ SE TÍM NIC NEROZBIJE. Odvozená hodnota je funkcí jemné, takže dvě slova
se stejným UPOS mají i stejnou třídu. Vektor se prodlouží, ale nerozdělí:
šablony, které splývaly, splývají dál, a šablony, které se lišily, se liší
dál. Při plném rozlišení je to zadarmo a smysl to dostane teprve tehdy, když
sítko pustí hrubou hodnotu a jemnou ne. Test to hlídá.

JAK SE PŘIDÁ DALŠÍ. Do tabulky ODVOZENE. Zdroj je jméno skupiny vertikál
(`UPOS`, `DEPREL`, `FEATS`), mapa je z jemné hodnoty na hrubou.
"""

from dataclasses import dataclass, field
from typing import Mapping, Sequence

# Plnovýznamová a pomocná slova podle UD. Rozdíl je v tom, jestli slovo něco
# znamená samo, nebo jen váže — a to je zrovna to, co na dálku potřebujeme
# vědět: „dvě slova vlevo stojí něco plnovýznamového" nese informaci, „dvě
# slova vlevo stojí zrovna NOUN v genitivu" už je na tu vzdálenost přepych.
PLNOVYZNAMOVE = ("NOUN", "PROPN", "VERB", "ADJ", "ADV", "INTJ")
POMOCNE = ("ADP", "AUX", "CCONJ", "DET", "NUM", "PART", "PRON", "SCONJ")

# Jádrové větné členy proti všemu ostatnímu. Totéž o patro výš: na dálku
# stačí vědět, že tam stojí podmět nebo předmět, ne který z nich.
JADROVE = ("nsubj", "obj", "iobj", "csubj", "ccomp", "xcomp", "root")
ROZVIJEJICI = ("amod", "nmod", "advmod", "acl", "advcl", "appos", "nummod",
               "obl", "obl:arg", "nsubj:pass", "det")


@dataclass(frozen=True)
class Odvozena:
    """Jedna hrubá vrstva nad jednou jemnou."""
    jmeno: str                      # „Trida" — jméno nového atributu
    skupina: str                    # skupina vertikál, ať se pozná v matici
    zdroj: str                      # skupina, ze které se čte („UPOS")
    mapa: Mapping[str, str] = field(default_factory=dict)
    jinak: str = "jiny"             # hodnota pro to, co v mapě není

    def hodnoty(self) -> list[str]:
        """Všechny hodnoty, kterých může nabýt — kvůli katalogu vertikál."""
        videno = list(dict.fromkeys(self.mapa.values()))
        if self.jinak not in videno:
            videno.append(self.jinak)
        return videno

    def vertikaly(self) -> list[dict]:
        return [{"a": f"{self.jmeno}={h}", "g": self.skupina}
                for h in self.hodnoty()]

    def odvodit(self, aktivace: Sequence[str], skupiny: Mapping[str, str]):
        """Hrubá hodnota pro tenhle token, nebo None, když zdroj chybí."""
        for a in aktivace:
            if skupiny.get(a) == self.zdroj:
                return f"{self.jmeno}={self.mapa.get(a, self.jinak)}"
        return None


def _mapa(*dvojice) -> dict:
    return {h: jmeno for jmena, jmeno in dvojice for h in jmena}


ODVOZENE = (
    Odvozena("Trida", "HRUBĚ", "UPOS",
             _mapa((PLNOVYZNAMOVE, "plny"), (POMOCNE, "pomocny"))),
    Odvozena("Uloha", "HRUBĚ", "DEPREL",
             _mapa((JADROVE, "jadro"), (ROZVIJEJICI, "rozvoj"))),
)


def vertikaly_odvozenych(odvozene: Sequence[Odvozena] = ODVOZENE) -> list[dict]:
    """Sloupce, které se přidají do katalogu. Na konec — kanonické pořadí je
    dané katalogem a hrubé vrstvy patří za jemné, ze kterých vznikly."""
    return [v for o in odvozene for v in o.vertikaly()]


def jmena_odvozenych(odvozene: Sequence[Odvozena] = ODVOZENE) -> set:
    return {v["a"] for v in vertikaly_odvozenych(odvozene)}


def bez_odvozenych(vertikaly: Sequence[Mapping],
                   odvozene: Sequence[Odvozena] = ODVOZENE) -> list[dict]:
    """Katalog očištěný o hrubé vrstvy — k uložení.

    Prohlížeč katalog dostane celý, včetně hrubých sloupců, protože je musí
    umět vykreslit. Kdyby je ale poslal zpátky k uložení, zapsaly by se mezi
    uložené a při dalším čtení by se přidaly podruhé. Počítané se neukládá."""
    jmena = jmena_odvozenych(odvozene)
    return [dict(c) for c in vertikaly if c.get("a") not in jmena]


def ocistit_korpus(vety: Sequence[Sequence[Mapping]],
                   odvozene: Sequence[Odvozena] = ODVOZENE) -> list:
    """Věty bez hrubých vrstev — k uložení.

    Prohlížeč věty dostane i s vrstvami, jinak by mřížka neseděla s vektorem.
    Zpátky ale nesmějí: kdyby se zapekly do korpusu, přestaly by být funkcí
    jemné hodnoty a při změně tabulky by v datech zůstala stará čísla."""
    jmena = jmena_odvozenych(odvozene)
    return [[dict(t, acts=[a for a in t.get("acts", ()) if a not in jmena])
             for t in veta] for veta in vety]
