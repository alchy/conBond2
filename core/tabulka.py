"""Přiřazovací tabulka — úlohy, kde má každý právě jedno od každého.

PROČ NE DIAGRAM. Šipkový diagram umí implikace mezi výroky, ale neumí říct
„právě jeden": že houslista je jediný, že každý má jiného malíře. Takové
tvrzení je součin („není to Josef ani Antonín ani Pavel ⇒ je to František")
a uzel se součinem v předpokladu diagram nemá. Fingovat to by znamenalo
tvrdit víc, než z něj plyne.

Úloha o milovnících umění (Bartlová, kap. 4.6) je proto jiný druh: čtyři
osoby, čtyři kategorie, a v každé kategorii je přiřazení VZÁJEMNĚ
JEDNOZNAČNÉ. Její přirozený tvar je tabulka — a to je tvar, který tenhle
projekt má jako svůj vlastní:

    řádky    osoby            = entity
    sloupce  kategorie        = atributy
    buňky    hodnoty          = to, co se hledá

Rozdíl proti poli je jediný, ale zásadní: v poli se hodnota ČTE z textu,
tady se DOPOČÍTÁVÁ z omezení. Je to táž tabulka, jen vyplňovaná z druhé
strany.

ČTYŘI DRUHY OMEZENÍ, a všechna jsou v té úloze potřeba:

    je(osoba, hodnota)        Antonín má nejraději baroko              (6)
    neni(osoba, hodnota)      František nehraje na basu                (2)
    spolu(hodnota, hodnota)   houslista má rád Kunderu                 (1)
    nikdy(hodnota, hodnota)   milovník gotiky není příznivec Cézanna  (10)

`spolu` a `nikdy` nejmenují osobu — to je na nich to podstatné. Říkají, že
JAKÁKOLI osoba s jednou hodnotou má (nebo nemá) i druhou, a právě tím se
kategorie provážou.

ÚPLNÉ PROHLEDÁNÍ, NE HEURISTIKA. Každá kategorie je permutace osob, takže
možností je (n!)^k — u čtyř osob a čtyř kategorií 331 776. To se projde
a je jistota, že řešení je JEDINÉ, nebo že jich je víc. Chytřejší
propagace by byla rychlejší, ale musela by se sama hlídat; tady se úplnost
kupuje za nic.

Vrací se VŠECHNA řešení, ne první nalezené. Úloha se dvěma řešeními vypadá
při vracení prvního jako vyřešená — a to je právě ta tichá chyba, kterou
tenhle projekt honí jinde.
"""

from itertools import permutations, product
from typing import Iterable, Mapping, Optional, Sequence


class Tabulka:
    """Osoby × kategorie, každá kategorie vzájemně jednoznačná."""

    def __init__(self, osoby: Sequence[str], kategorie: Mapping):
        self.osoby = list(osoby)
        self.kategorie = {k: list(v) for k, v in kategorie.items()}
        for k, v in self.kategorie.items():
            if len(v) != len(self.osoby):
                raise ValueError(
                    f"kategorie {k!r} má {len(v)} hodnot na {len(self.osoby)} osob; "
                    "přiřazení nemůže být vzájemně jednoznačné")
        self.omezeni: list = []
        # hodnota → kategorie, aby `spolu`/`nikdy` nemusely kategorii uvádět.
        # Kdyby se táž hodnota objevila ve dvou kategoriích, nešlo by to
        # rozhodnout — proto raději výjimka než tichý výběr první.
        self.kde: dict = {}
        for k, hodnoty in self.kategorie.items():
            for h in hodnoty:
                if h in self.kde:
                    raise ValueError(f"hodnota {h!r} je ve dvou kategoriích")
                self.kde[h] = k

    # ---- omezení -----------------------------------------------------
    def je(self, osoba: str, hodnota: str, cislo: str = "") -> "Tabulka":
        self.omezeni.append(("je", osoba, hodnota, cislo))
        return self

    def neni(self, osoba: str, hodnota: str, cislo: str = "") -> "Tabulka":
        self.omezeni.append(("neni", osoba, hodnota, cislo))
        return self

    def spolu(self, a: str, b: str, cislo: str = "") -> "Tabulka":
        """Kdo má `a`, má i `b` — bez ohledu na to, kdo to je."""
        self.omezeni.append(("spolu", a, b, cislo))
        return self

    def nikdy(self, a: str, b: str, cislo: str = "") -> "Tabulka":
        """Nikdo nemá `a` a `b` zároveň."""
        self.omezeni.append(("nikdy", a, b, cislo))
        return self

    # ---- řešení ------------------------------------------------------
    def _sedi(self, prirazeni: Mapping) -> Optional[str]:
        """None, když vyhovuje; jinak číslo omezení, o které to zavadilo.

        Vrací se, KTERÉ omezení spadlo, ne jen že spadlo — u úlohy bez
        řešení je to jediné vodítko, kde je chyba v zadání."""
        def kdo_ma(h):
            return prirazeni[self.kde[h]].get(h)

        for druh, a, b, cislo in self.omezeni:
            if druh == "je" and kdo_ma(b) != a:
                return cislo or f"je({a}, {b})"
            if druh == "neni" and kdo_ma(b) == a:
                return cislo or f"není({a}, {b})"
            if druh == "spolu" and kdo_ma(a) != kdo_ma(b):
                return cislo or f"spolu({a}, {b})"
            if druh == "nikdy" and kdo_ma(a) == kdo_ma(b):
                return cislo or f"nikdy({a}, {b})"
        return None

    def resit(self) -> list:
        """Všechna řešení jako {kategorie: {hodnota: osoba}}."""
        jmena = sorted(self.kategorie)
        varianty = [[dict(zip(self.kategorie[k], p))
                     for p in permutations(self.osoby)] for k in jmena]
        out = []
        for kombinace in product(*varianty):
            prirazeni = dict(zip(jmena, kombinace))
            if self._sedi(prirazeni) is None:
                out.append(prirazeni)
        return out

    def podle_osob(self, prirazeni: Mapping) -> dict:
        """Přehození na {osoba: {kategorie: hodnota}} — jak se to čte."""
        out = {o: {} for o in self.osoby}
        for kat, mapa in prirazeni.items():
            for hodnota, osoba in mapa.items():
                out[osoba][kat] = hodnota
        return out
