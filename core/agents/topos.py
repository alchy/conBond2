"""Topos — agent MÍSTO.

Převzato z conBond, kde rozlišoval, zda lemma je GEO entita, podle
gazetteeru. Gazetteer jsou DATA, třída je čistý MECHANISMUS — to rozdělení
přebíráme.

Bez seznamu míst umí Topos jen to, co dá rozbor: vlastní jméno s rysem
`NameType=Geo`. Je to méně, než uměl původní Topos s gazetteerem, ale je to
poctivé — a `NameType=Geo` je mimochodem rys, který jsem chtěl v revizi
škrtnout jako zbytečný. Ukazuje se, že zbytečný je jako sloupec ve vektoru,
ale užitečný jako VSTUP pro agenta.
"""

from typing import Iterable, Optional, Sequence

from .base import Agent, Naveska


class Topos(Agent):
    jmeno = "topos"
    typ = "Typ=misto"

    def __init__(self, gazetteer: Optional[Iterable[str]] = None):
        self.gazetteer = {g.lower() for g in (gazetteer or ())}

    def je_misto(self, t: dict) -> bool:
        if any(a.startswith("NameType=") and "Geo" in a for a in t["acts"]):
            return True
        return t["form"].lower() in self.gazetteer

    def najdi(self, veta: Sequence[dict]) -> list:
        return [Naveska(rozsah=[i], hlava=i, typ=self.typ,
                        hodnota=t["form"], zdroj=self.jmeno)
                for i, t in enumerate(veta) if self.je_misto(t)]
