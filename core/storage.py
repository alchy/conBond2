"""Výchozí úložiště: JSON soubory, podadresář na každou datovou strukturu.

    data/
    ├── verticals/verticals.json     sloupce pole
    ├── corpora/facts.json           věty textu
    ├── corpora/query.json           dotazy
    ├── mappings/q1f1.json           dvojice pro jednu dvojici poloměrů
    └── defaults/…                   zdrojová sada, ze které se zakládá

Všechno JSON a odsazené — datové struktury mají zůstat čitelné okem. Žádné
pickle: co se nedá otevřít v editoru, se nedá ani opravit ani přečíst za pět
let.

Mapování má soubor na KAŽDOU DVOJICI poloměrů. Šablony dotazů závisí na r_q,
šablony faktů na r_f, a ta dvě r se smí lišit; jeden společný soubor by
tvrdil, že mapování z r=1 platí i pro r=4.
"""

import json
import os
import re
from typing import Iterable, Mapping, Sequence

from .config import PODADRESARE, Config
from .interfaces import Uloziste

KLIC_MAPOVANI = re.compile(r"^q[0-8]f[0-8]$")

# Každý datový typ má svou složku — proto se cesta skládá z podadresáře
# podle struktury a jména souboru, ne z jedné natvrdo psané cesty.
STRUKTURY = {
    "verticals": ("verticals", "verticals.json"),
    "facts": ("corpora", "facts.json"),
    "query": ("corpora", "query.json"),
}


class UlozisteSouboru(Uloziste):
    def __init__(self, koren=None, config: Config = None):
        """Buď cesta, nebo Config. Config umí data přesměrovat jinam —
        pro testy, pro druhý korpus, pro porovnání dvou sad vedle sebe."""
        self.config = config or Config(data=koren or "data")
        self.koren = self.config.data
        self.vychozi = self.config.slozka("defaults")
        self._pamet: dict[str, object] = {}

    # ---- cesty -------------------------------------------------------
    def cesta(self, *kusy: str) -> str:
        return os.path.join(self.koren, *kusy)

    def cesta_struktury(self, jmeno: str) -> str:
        if jmeno not in STRUKTURY:
            raise KeyError(f"neznámá struktura {jmeno!r}")
        slozka, soubor = STRUKTURY[jmeno]
        return os.path.join(self.config.slozka(slozka), soubor)

    def cesta_mapovani(self, klic: str) -> str:
        self.overit_klic(klic)
        return os.path.join(self.config.slozka("mappings"), klic + ".json")

    @staticmethod
    def overit_klic(klic: str) -> str:
        if not KLIC_MAPOVANI.match(klic or ""):
            raise ValueError(f"klíč mapování musí být q<0-8>f<0-8>, ne {klic!r}")
        return klic

    # ---- čtení a zápis ------------------------------------------------
    def precist(self, cesta: str, kdyz_chybi=None):
        try:
            with open(cesta, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return kdyz_chybi

    def zapsat(self, cesta: str, obsah) -> None:
        """Přes dočasný soubor a přejmenování — kdyby to spadlo uprostřed,
        zůstane na místě celý starý soubor místo půlky nového."""
        os.makedirs(os.path.dirname(cesta), exist_ok=True)
        docasny = cesta + ".tmp"
        with open(docasny, "w", encoding="utf-8") as f:
            json.dump(obsah, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(docasny, cesta)

    # ---- rozhraní Uloziste -------------------------------------------
    def nacist_vertikaly(self) -> Sequence[Mapping]:
        return self._nacist_strukturu("verticals")

    def nacist_korpus(self, strana: str) -> Sequence[Sequence[Mapping]]:
        if strana not in ("facts", "query"):
            raise KeyError(f"korpus je 'facts' nebo 'query', ne {strana!r}")
        return self._nacist_strukturu(strana)

    def _nacist_strukturu(self, jmeno: str):
        """Když struktura ještě není, vezme se výchozí sada — pracovní kopie
        se založí až prvním zápisem."""
        if jmeno in self._pamet:
            return self._pamet[jmeno]
        obsah = self.precist(self.cesta_struktury(jmeno))
        if obsah is None:
            obsah = self.precist(os.path.join(self.vychozi, jmeno + ".json"), [])
        self._pamet[jmeno] = obsah
        return obsah

    def ulozit_vertikaly(self, vertikaly) -> None:
        self._ulozit_strukturu("verticals", vertikaly)

    def ulozit_korpus(self, strana: str, vety) -> None:
        self._ulozit_strukturu(strana, vety)

    def _ulozit_strukturu(self, jmeno: str, obsah) -> None:
        self._pamet[jmeno] = obsah
        self.zapsat(self.cesta_struktury(jmeno), obsah)

    def nacist_mapovani(self, klic: str) -> Sequence[Mapping]:
        obsah = self.precist(self.cesta_mapovani(klic))
        if obsah is None:
            obsah = self.precist(os.path.join(self.vychozi, "mappings.json"), [])
        return obsah

    def ma_mapovani(self, klic: str) -> bool:
        return os.path.exists(self.cesta_mapovani(klic))

    def ulozit_mapovani(self, klic: str, dvojice: Iterable[Mapping]) -> None:
        self.zapsat(self.cesta_mapovani(klic), list(dvojice))

    def vypsat_mapovani(self) -> dict:
        kam = self.config.slozka("mappings")
        if not os.path.isdir(kam):
            return {}
        return {jm[:-5]: self.precist(os.path.join(kam, jm), [])
                for jm in sorted(os.listdir(kam)) if jm.endswith(".json")}

    # ---- návrat k výchozímu ------------------------------------------
    def vratit_vychozi(self) -> None:
        """Zahodí pracovní kopie struktur. Mapování zůstane."""
        self._pamet.clear()
        for jmeno in STRUKTURY:
            cesta = self.cesta_struktury(jmeno)
            if os.path.exists(cesta):
                os.remove(cesta)
