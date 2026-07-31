"""Metron — agent POČET a MÍRA.

Převzato z conBond. Doménově slepý: žádný seznam jednotek, žádné if-then per
obor — rozhoduje jen gramatický rys `NumType` a slovní druh `NUM`.

Dělba s Chronem je z conBondu a je podstatná: **čtyřmístný rok není počet**.
Bez toho by „1914" a „430" byly v poli totéž (`NUM nummod Card Digit`) a
právě tyhle vzory nám ovládly statistiku sdílení.

Do vektoru jde `Typ=pocet`, hodnota zůstává mimo — číslic je v korpusu přes
čtyři tisíce a jako aktivace by to byly tisíce sloupců, z nichž většina
jednorázových.
"""

from typing import Sequence

from .base import Agent, Naveska, je_cislo, v_zavorce


class Metron(Agent):
    jmeno = "metron"
    typ = "Typ=pocet"

    def __init__(self, rok_od: int = 1000, rok_do: int = 2100):
        self.rok_od = rok_od
        self.rok_do = rok_do

    def je_rok(self, forma: str) -> bool:
        return (forma.isdigit() and len(forma) == 4
                and self.rok_od <= int(forma) <= self.rok_do)

    def najdi(self, veta: Sequence[dict]) -> list:
        out = []
        for i, t in enumerate(veta):
            if not je_cislo(t):
                continue
            if self.je_rok(t["form"]):
                continue                      # doména Chronose
            if v_zavorce(veta, i):
                continue                      # lokální vsuvka
            if "Typ=cas" in t["acts"]:
                continue                      # už si to vzal Chronos
            out.append(Naveska(rozsah=[i], hlava=i, typ=self.typ,
                               hodnota=self.hodnota(t), zdroj=self.jmeno))
        return out

    @staticmethod
    def hodnota(t: dict):
        """Číslicí přesně, slovem jen jako tvar — číslovkový lexikon zatím
        nemáme a hádat ho nebudeme."""
        return int(t["form"]) if t["form"].isdigit() else t["form"].lower()
