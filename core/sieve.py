"""Které aktivace se z kterého offsetu do vektoru dostanou.

VZNIKLO Z MĚŘENÍ. Střed do svého vlastního vektoru nevstupoval, takže cokoli,
co v češtině nese slovo samo, bylo pro jeho šablonu neviditelné — zápor
(`Polarity`), čas, osoba, způsob. „Brno je město" a „Brno není město" daly
znak po znaku týž vektor a spadly do jedné šablony.

Pustit dovnitř celý střed to spraví, ale zabije sdílení: na spisovatelském
korpusu klesl podíl slov ve sdílených vzorech z 57 % na 27 %, protože šablona
přestala být obálkou OKOLÍ a stala se popisem toho slova — rozpadla se podle
pádu, čísla a rodu středu. Vzor „…a X." sdílelo 189 různých slov; se středem
uvnitř z toho bylo 92 šablon.

Sítko je ta střední cesta: střed do okna vpustíme, ale projde z něj jen to,
co jmenujeme. `stred_atributy = ("Polarity",)` udrží sdílení a zápor přesto
uvidí.

Šev, ne `if` v jádře — kdo chce sítko podle jiného klíče (třeba propouštět
podle jistoty nebo podle zdroje aktivace), podstrčí vlastní třídu.
"""

from typing import Iterable, Mapping, Sequence

from .interfaces import Sitko


def jmeno_aktivace(aktivace: str) -> str:
    """`Polarity=Neg` → `Polarity`; `AUX` zůstane `AUX`."""
    return aktivace.split("=", 1)[0]


class SitkoVse(Sitko):
    """Propouští všechno — chování pole, dokud se sítko nezavede."""

    def propustit(self, offset: int, aktivace: Sequence[str]) -> list[str]:
        return list(aktivace)

    def je_cinne(self) -> bool:
        return False


class SitkoStredu(Sitko):
    """Sousedy propouští celé, střed jen ve jmenovaných atributech.

    Jméno se dá napsat na třech úrovních a stačí, když sedí jedna:

        "Polarity=Neg"   přesná aktivace
        "Polarity"       atribut bez ohledu na hodnotu
        "FEATS"          celá skupina vertikál

    Prázdný seznam znamená „nefiltruj" — pak je to totéž co SitkoVse a pole
    se chová jako dřív.
    """

    def __init__(self, povolene: Iterable[str] = (),
                 vertikaly: Sequence[Mapping] = ()):
        self.povolene = tuple(dict.fromkeys(povolene))
        self.skupiny = {c["a"]: c.get("g", "") for c in vertikaly}

    def je_cinne(self) -> bool:
        return bool(self.povolene)

    def propustit(self, offset: int, aktivace: Sequence[str]) -> list[str]:
        if offset != 0 or not self.povolene:
            return list(aktivace)
        return [a for a in aktivace if self.projde(a)]

    def projde(self, aktivace: str) -> bool:
        return (aktivace in self.povolene
                or jmeno_aktivace(aktivace) in self.povolene
                or self.skupiny.get(aktivace, "") in self.povolene)

    def __repr__(self) -> str:
        return f"SitkoStredu({', '.join(self.povolene) or 'vše'})"
