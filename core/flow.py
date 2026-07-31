"""Krok 1 workflow: rozprostřít věty do pole.

Každá věta dostane r prázdných řádků na obou koncích. Mezi posledním slovem
jedné věty a prvním slovem druhé tak leží vždy 2r prázdných řádků a okno
NEMÁ JAK přelézt hranici — hranici drží sama geometrie. Rám věty ani poloměr
ve větách proto nejsou potřeba.
"""

from dataclasses import dataclass
from typing import Iterator, Mapping, Optional, Sequence

from .interfaces import ZdrojAktivaci


@dataclass(slots=True)
class Radek:
    """Jeden řádek pole. Prázdný slot nemá token."""
    veta: int
    token: Optional[Mapping] = None
    poradi_ve_vete: int = -1

    @property
    def je_prazdny(self) -> bool:
        return self.token is None


class Tok:
    """Věty srovnané za sebou i s odsazením."""

    def __init__(self, zdroj: ZdrojAktivaci, polomer: int, syrove: bool = False):
        self.zdroj = zdroj
        self.polomer = polomer
        self.syrove = syrove
        self.radky: list[Radek] = []

    # ---- stavba ------------------------------------------------------
    def rozprostrit(self, vety: Sequence[Sequence[Mapping]]) -> "Tok":
        self.radky = []
        for cislo, veta in enumerate(vety):
            self.radky.extend(self.odsadit_vetu(cislo, veta))
        return self

    def odsadit_vetu(self, cislo: int, veta: Sequence[Mapping]) -> Iterator[Radek]:
        yield from self.vyrobit_prazdne(cislo)
        for poradi, token in enumerate(self.vybrat_tokeny(veta)):
            yield Radek(veta=cislo, token=token, poradi_ve_vete=poradi)
        yield from self.vyrobit_prazdne(cislo)

    def vyrobit_prazdne(self, cislo: int) -> Iterator[Radek]:
        for _ in range(self.polomer):
            yield Radek(veta=cislo)

    def vybrat_tokeny(self, veta: Sequence[Mapping]) -> list[Mapping]:
        """Zrno textu: normalizovaně jde interpunkce stranou."""
        if self.syrove:
            return list(veta)
        return [t for t in veta if not self.zdroj.je_interpunkce(t)]

    # ---- čtení -------------------------------------------------------
    def radek(self, i: int) -> Optional[Radek]:
        return self.radky[i] if 0 <= i < len(self.radky) else None

    def vypsat_stredy(self) -> list[tuple[int, Radek]]:
        """Řádky, které jsou slovo — tedy možné středy vektoru."""
        return [(i, x) for i, x in enumerate(self.radky) if not x.je_prazdny]

    def pocet_radku(self) -> int:
        return len(self.radky)

    def __len__(self) -> int:
        return len(self.radky)
