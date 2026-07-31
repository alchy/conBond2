"""Specializovaní agenti — každý jednu doménu.

Převzato z conBond, kde to byl Chronos (čas), Topos (místo) a Metron (počet).
Tady mají jinou úlohu: nevytěžují fakt, ale **dodávají do pole aktivace**.
Jsou tedy implementací švu `ZdrojAktivaci` — druhý zdroj vedle UDPipe.

ROZDĚLENÍ NA TYP A HODNOTU je to podstatné, co se tím získá.

Agent nenajde jen „tady je čas", ale i „a je to rok 1914". Kdyby obojí šlo do
vektoru, vzniklo by 244 sloupců `Rok=…` (tolik je různých roků v korpusu) a
19 % z nich by se vyskytlo jen jednou — takové šablony se nemohou sdílet
nikdy. Cena atributu je pokrytí × kardinalita a tohle je nejhorší možná
kombinace.

Proto:

    typ      Typ=cas       jde do aktivací → do vektoru → ZOBECŇUJE
    hodnota  1914-03-28    jde MIMO aktivace → na vazbu → ROZLIŠUJE

Hodnota se ukládá do tokenu pod klíč `hodnota`, ne do `acts`. Tím se do
vektoru nemůže dostat ani omylem — jádro čte výhradně `acts`.

Šablona pak nese TVAR („v tomhle místě je čas"), vazba nese OBSAH („a je to
rok 1914"). Bez toho rozdělení se nedá mít zároveň hrubá šablona, která se
sdílí, a přesná odpověď.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence


@dataclass
class Naveska:
    """Co agent na místě v textu našel.

    `rozsah` je nutný, protože nálezy jsou často víceslovné: „28. března 1914"
    jsou čtyři tokeny a jeden čas. Aktivace se pověsí na hlavu rozsahu, aby
    pole zůstalo jeden řádek na token.
    """
    rozsah: Sequence[int]        # indexy tokenů ve větě
    hlava: int                   # na který token se pověsí aktivace
    typ: str                     # aktivace do vektoru, např. "Typ=cas"
    hodnota: Any = None          # normalizovaná hodnota — do vektoru NEJDE
    zdroj: str = ""              # který agent to našel
    jistota: float = 1.0

    def do_slovniku(self) -> dict:
        return {"rozsah": list(self.rozsah), "typ": self.typ,
                "hodnota": self.hodnota, "zdroj": self.zdroj,
                "jistota": self.jistota}


class Agent(ABC):
    """Expert na jednu doménu. Čte větu, vrací návěsky."""

    jmeno = "agent"
    typ = ""

    @abstractmethod
    def najdi(self, veta: Sequence[dict]) -> list:
        """Nálezy v jedné větě. Věta je seznam tokenů {form, upos, acts, …}."""

    def oznac(self, veta: Sequence[dict]) -> int:
        """Zapíše nálezy do věty. Typ do `acts`, hodnota mimo ně."""
        kolik = 0
        for n in self.najdi(veta):
            token = veta[n.hlava]
            if n.typ and n.typ not in token["acts"]:
                token["acts"].append(n.typ)
            if n.hodnota is not None:
                # MIMO acts — jádro čte jen acts, takže se hodnota nemůže
                # dostat do vektoru ani omylem.
                token.setdefault("hodnota", {})[self.jmeno] = n.hodnota
            token.setdefault("navesky", []).append(n.do_slovniku())
            kolik += 1
        return kolik


# ---- sdílené pomůcky -----------------------------------------------------
def v_zavorce(veta: Sequence[dict], i: int) -> bool:
    """Je token uvnitř závorky?

    Lekce z Chronose, získaná měřením, ne úvahou: závorka je lokální vsuvka.
    Bez tohohle řezu věta „Narodil se … Marii (1894 – 1970) a Bohumilu
    (1893 …)" přivěsila roky RODIČŮ k narození protagonisty. V našich
    životopisech jsou takové závorky všude.
    """
    hloubka = 0
    for j, t in enumerate(veta):
        if t["form"] in ("(", "["):
            hloubka += 1
        elif t["form"] in (")", "]"):
            hloubka = max(0, hloubka - 1)
        elif j == i:
            return hloubka > 0
    return False


def je_cele_cislo(forma: str) -> bool:
    """Dá se ten tvar přečíst jako celé číslo?

    NE `isdigit()`. Ten vrací True i pro „²" (a pro arabské číslice), takže
    `int()` na něm spadne — a spadl: článek o betonu má „m²" a shodil celou
    stavbu korpusu na 86 článcích. `isdecimal()` je právě ten predikát, po
    kterém `int()` projde vždycky."""
    return forma.isdecimal()


def je_cislo(token: dict) -> bool:
    return token["upos"] == "NUM" or any(
        a.startswith("NumType=") for a in token["acts"])
