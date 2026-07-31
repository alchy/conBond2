"""Úložné: JSON soubory. Nic víc — kdo chce vědět o HTTP, ať jde do routy.py.

Mapování má vlastní soubor pro KAŽDOU DVOJICI poloměrů. Šablony dotazů
závisí na r_q, šablony faktů na r_f, a ta dvě r se smí lišit. Jeden společný
soubor by tvrdil, že mapování z r=1 platí i pro r=4 — a to není pravda, je
to jiné rozlišení téhož textu.
"""

import json
import os
import re

KLIC = re.compile(r"^q[0-8]f[0-8]$")


class Ulozne:
    def __init__(self, koren):
        self.data = os.path.join(koren, "data")
        self.mapy = os.path.join(self.data, "maps")
        os.makedirs(self.mapy, exist_ok=True)

    # ---- stav ----------------------------------------------------------
    @property
    def _stav(self):
        return os.path.join(self.data, "stav.json")

    def ma_stav(self):
        return os.path.exists(self._stav)

    def cti_stav(self):
        return _cti(self._stav)

    def zapis_stav(self, obj):
        _zapis(self._stav, obj)

    # ---- mapování ------------------------------------------------------
    def _soubor_mapy(self, klic):
        return os.path.join(self.mapy, klic + ".json")

    @staticmethod
    def platny_klic(klic):
        return bool(KLIC.match(klic))

    def ma_mapu(self, klic):
        return os.path.exists(self._soubor_mapy(klic))

    def cti_mapu(self, klic):
        return _cti(self._soubor_mapy(klic))

    def zapis_mapu(self, klic, seznam):
        _zapis(self._soubor_mapy(klic), seznam)

    def vsechny_mapy(self):
        out = {}
        if os.path.isdir(self.mapy):
            for jm in sorted(os.listdir(self.mapy)):
                if jm.endswith(".json"):
                    out[jm[:-5]] = _cti(os.path.join(self.mapy, jm)) or []
        return out


def _cti(cesta):
    try:
        with open(cesta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _zapis(cesta, obj):
    """Přes dočasný soubor a přejmenování. Kdyby to spadlo uprostřed, zůstane
    na místě celý starý soubor místo půlky nového."""
    os.makedirs(os.path.dirname(cesta), exist_ok=True)
    doc = cesta + ".tmp"
    with open(doc, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(doc, cesta)
