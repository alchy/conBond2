"""Krok 2 workflow: určit, kam kolem středu vektor dopadá.

Díky odsazení v toku je to čisté počítání indexů — sloty středu i jsou
i-r … i+r a všechny vždycky existují. Dřívější verze musela hlídat okraje
pole i hranice vět; odsazení tu práci udělalo za ni.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Slot:
    j: int      # index řádku v toku
    d: int      # offset od středu


def zapsat_offset(d: int) -> str:
    return f"+{d}" if d > 0 else str(d)


class Okno:
    """Okolí středu při daném poloměru."""

    def __init__(self, polomer: int, stred_uvnitr: bool = False):
        self.polomer = polomer
        self.stred_uvnitr = stred_uvnitr

    def urcit_sloty(self, stred: int) -> list[Slot]:
        if self.polomer == 0:
            return [Slot(stred, 0)]
        return [Slot(stred + d, d) for d in self.offsety()]

    def offsety(self) -> list[int]:
        if self.polomer == 0:
            return [0]
        out = []
        for d in range(-self.polomer, self.polomer + 1):
            if d == 0 and not self.stred_uvnitr:
                continue
            out.append(d)
        return out

    def pocet_slotu(self) -> int:
        return len(self.offsety())

    def zasahuje(self, d: int) -> bool:
        """Vejde se offset do okna? Podle toho se v paletě šedne."""
        if self.polomer == 0:
            return d == 0
        if d == 0:
            return self.stred_uvnitr
        return abs(d) <= self.polomer
