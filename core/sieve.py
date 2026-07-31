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


# Aktivace, kterou žádné sítko nemůže znát — slouží jako zkouška.
ZKOUSKA = "\x00zkouška"


def filtruje_stred(sitko: Sitko) -> bool:
    """Zahodí sítko na offsetu 0 neznámou aktivaci?

    Sítko, které střed filtruje, je bez `stred_uvnitr` k ničemu: offset 0
    není slot, takže se ho nikdo nezeptá. Přes setter `stred_atributy` se to
    srovná samo, ale sítko podstrčené jako šev tudy nejde a chyba je němá —
    vypadá to, že se filtruje, a přitom se nefiltruje nic. Odtud tahle
    zkouška: jádro se zeptá a když to nesedí, řekne to."""
    return list(sitko.propustit(0, [ZKOUSKA])) != [ZKOUSKA]


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


class SitkoStupnovane(Sitko):
    """Rozlišení klesá se vzdáleností od středu.

    Blízko všechno, daleko jen hrubá třída. Změřeno na spisovatelském
    korpusu, střed = Polarity:

        r=1, dál nic                   52 % slov ve sdílených vzorech
        r=2, na ±2 vše                 10 %
        r=2, na ±2 jen UPOS            24 %
        r=2, na ±2 třída o 3 hodnotách 38 %

    Dohlédnout o slovo dál stojí 42 bodů sdílení plným pohledem a 14 bodů
    hrubým. Je to týž zákon jako u výběru atributů — cena ≈ pokrytí ×
    mohutnost —, jen zapsaný přes vzdálenost.

    Patra se zadávají podle |offsetu|; klíč None je zbytek:

        {0: ("Polarity",), 1: (), None: ("Trida",)}

    Prázdná n-tice znamená „vše". Pozor, patro, které nepustí NIC, splyne
    s prázdným slotem — takový offset pak nerozliší ani „je tam něco" od
    „je tam konec věty", takže je to totéž jako menší poloměr.

    STŘED SE MUSÍ POJMENOVAT. Klíč None zbytek nezahrnuje offset 0; kdo píše
    útlum podle vzdálenosti, na střed nemyslí, a tiché oříznutí středu by
    bylo překvapení. Bez klíče 0 projde střed celý.
    """

    def __init__(self, patra: Mapping[object, Sequence[str]],
                 vertikaly: Sequence[Mapping] = ()):
        self.patra = dict(patra)
        self.skupiny = {c["a"]: c.get("g", "") for c in vertikaly}

    def je_cinne(self) -> bool:
        return any(self.patra.values())

    def povolene(self, offset: int) -> Sequence[str]:
        if offset == 0:
            return self.patra.get(0, ())      # zbytek se středu netýká
        return self.patra.get(abs(offset), self.patra.get(None, ()))

    def propustit(self, offset: int, aktivace: Sequence[str]) -> list[str]:
        pov = self.povolene(offset)
        if not pov:
            return list(aktivace)
        return [a for a in aktivace if self.projde(a, pov)]

    def projde(self, aktivace: str, pov: Sequence[str]) -> bool:
        return (aktivace in pov
                or jmeno_aktivace(aktivace) in pov
                or self.skupiny.get(aktivace, "") in pov)

    def __repr__(self) -> str:
        patra = ", ".join(f"{k}:{'/'.join(v) or 'vše'}"
                          for k, v in sorted(self.patra.items(), key=lambda x: str(x[0])))
        return f"SitkoStupnovane({patra})"
