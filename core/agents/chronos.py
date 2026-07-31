"""Chronos — agent ČAS.

Převzato z conBond. Tam vytěžoval rok a věšel ho na predikát; tady dodává do
pole aktivaci `Typ=cas` a k ní normalizovanou hodnotu, která do vektoru
NEJDE.

Proč to pole potřebuje: datum je v textu čtyři tokeny („28 . března 1914")
a v našem korpusu to byly nejčastější sdílené vzory vůbec — 363 a 283
výskytů. Statistika sdílení tak měřila hlavně wikipediovskou datovou omáčku,
ne jazykové zobecnění. Agent to scelí do jednoho nálezu: čtyři řádky pole
zůstanou, ale nesou jeden čas s jednou hodnotou.

Pravidla jsou z conBondu, obě vzniklá měřením:

  * ROK je čtyřmístné číslo v rozsahu (1000–2100), aby „123" ani „9999"
    nebyly rok.
  * ROKY V ZÁVORCE se přeskakují — závorka je lokální vsuvka a její čas
    nepatří hlavnímu ději věty.
"""

import re
from typing import Sequence

from .base import Agent, Naveska, v_zavorce

MESICE = {
    "leden": 1, "ledna": 1, "únor": 2, "února": 2, "březen": 3, "března": 3,
    "duben": 4, "dubna": 4, "květen": 5, "května": 5, "červen": 6, "června": 6,
    "červenec": 7, "července": 7, "srpen": 8, "srpna": 8, "září": 9,
    "říjen": 10, "října": 10, "listopad": 11, "listopadu": 11,
    "prosinec": 12, "prosince": 12,
}
# „v roce", „r." — slovo, které rok uvozuje a patří do rozsahu nálezu
UVOZUJE = {"rok", "roce", "roku", "r", "léta", "letech", "století", "stol"}


class Chronos(Agent):
    jmeno = "chronos"
    typ = "Typ=cas"

    def __init__(self, rok_od: int = 1000, rok_do: int = 2100):
        self.rok_od = rok_od
        self.rok_do = rok_do

    # ---- rozpoznání --------------------------------------------------
    def je_rok(self, forma: str) -> bool:
        return (forma.isdigit() and len(forma) == 4
                and self.rok_od <= int(forma) <= self.rok_do)

    @staticmethod
    def je_den(forma: str) -> bool:
        """Den v datu se v češtině píše s tečkou: „28.". UDPipe tečku
        odděluje, takže sem přijde holé číslo a tečka je další token."""
        return forma.isdigit() and 1 <= len(forma) <= 2 and 1 <= int(forma) <= 31

    @staticmethod
    def mesic(forma: str):
        return MESICE.get(forma.lower())

    # ---- hledání -----------------------------------------------------
    def najdi(self, veta: Sequence[dict]) -> list:
        out, i = [], 0
        while i < len(veta):
            n = self.datum_od(veta, i) or self.rok_od_pozice(veta, i)
            if n is None:
                i += 1
                continue
            out.append(n)
            i = max(n.rozsah) + 1
        return out

    def datum_od(self, veta: Sequence[dict], i: int):
        """Plné datum „28 . března 1914" nebo „28. března"."""
        if not self.je_den(veta[i]["form"]):
            return None
        j = i + 1
        if j < len(veta) and veta[j]["form"] == ".":
            j += 1
        if j >= len(veta):
            return None
        m = self.mesic(veta[j]["form"])
        if m is None:
            return None
        rozsah = list(range(i, j + 1))
        den, rok = int(veta[i]["form"]), None
        if j + 1 < len(veta) and self.je_rok(veta[j + 1]["form"]):
            rok = int(veta[j + 1]["form"])
            rozsah.append(j + 1)
        if v_zavorce(veta, i):
            return None
        hodnota = f"{rok:04d}-{m:02d}-{den:02d}" if rok else f"--{m:02d}-{den:02d}"
        return Naveska(rozsah=rozsah, hlava=rozsah[-1], typ=self.typ,
                       hodnota=hodnota, zdroj=self.jmeno,
                       jistota=1.0 if rok else 0.8)

    def rok_od_pozice(self, veta: Sequence[dict], i: int):
        """Samotný rok, případně i s uvozujícím slovem („v roce 1914")."""
        if not self.je_rok(veta[i]["form"]):
            return None
        if v_zavorce(veta, i):
            return None
        rozsah = [i]
        if i > 0 and veta[i - 1]["form"].lower().rstrip(".") in UVOZUJE:
            rozsah.insert(0, i - 1)
        return Naveska(rozsah=rozsah, hlava=i, typ=self.typ,
                       hodnota=int(veta[i]["form"]), zdroj=self.jmeno)
