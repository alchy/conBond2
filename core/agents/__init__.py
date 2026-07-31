"""Specializovaní agenti — každý jednu doménu, každý zdroj aktivací pro pole.

    from core.agents import Chronos, Metron, Topos, oznacit_korpus

Typ jde do vektoru a zobecňuje, hodnota zůstane na vazbě a rozlišuje. Viz
base.py, kde je ten rozdíl vysvětlený i s čísly, proč na něm záleží.
"""

from .base import Agent, Naveska, je_cislo, v_zavorce
from .chronos import Chronos
from .metron import Metron
from .topos import Topos

VYCHOZI = (Chronos, Metron, Topos)

__all__ = ["Agent", "Naveska", "Chronos", "Metron", "Topos",
           "oznacit_korpus", "VYCHOZI", "je_cislo", "v_zavorce"]


def oznacit_korpus(vety, agenti=None) -> dict:
    """Pustí agenty na korpus. Pořadí je významné: Chronos si první vezme
    roky, aby je Metron nepočítal jako počty."""
    agenti = list(agenti or [t() for t in VYCHOZI])
    souhrn = {a.jmeno: 0 for a in agenti}
    for veta in vety:
        for a in agenti:
            souhrn[a.jmeno] += a.oznac(veta)
    return souhrn
