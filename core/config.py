"""Konfigurace — hlavně kde leží data.

Aby šlo pole postavit nad jinou složkou, než je ta pracovní: pro testy, pro
druhý korpus, pro porovnání dvou sad vedle sebe. Nikde v jádře proto není
cesta natvrdo; všechno jde přes tohle.

Pořadí, ve kterém se konfigurace bere (co je níž, přebíjí):

    1. výchozí hodnoty
    2. config.json v kořeni projektu
    3. proměnné prostředí POLE2_*
    4. co se předá přímo v kódu

Poslední bod je pro testy ten podstatný:

    from core import Config, Pole, UlozisteSouboru
    conf = Config(data="/tmp/zkouska")
    pole = Pole(UlozisteSouboru(conf.data))
"""

import json
import os
from dataclasses import dataclass, field, fields
from typing import Optional

KOREN_PROJEKTU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Podadresář na každou datovou strukturu. Jména jsou tu, aby je nemusel
# nikdo hádat z cest rozesetých po kódu.
PODADRESARE = {
    "verticals": "verticals",
    "corpora": "corpora",
    "mappings": "mappings",
    "defaults": "defaults",
}

PREDPONA_ENV = "POLE2_"


@dataclass
class Config:
    """Porty jsou schválně mimo obvyklá čísla: 8000, 8001 a 8112 už na
    vývojovém stroji drží jiné projekty a kolize se hledá blbě."""
    data: str = "data"
    port: int = 9000            # naše API a stránka
    udpipe_port: int = 9010     # rozbor vět
    udpipe_host: str = "127.0.0.1"
    log_uroven: str = "info"      # ticho | info | debug
    log_soubor: str = "run/core.log"
    koren: str = KOREN_PROJEKTU

    def __post_init__(self) -> None:
        self.data = self.absolutni(self.data)
        self.port = int(self.port)
        self.udpipe_port = int(self.udpipe_port)

    @property
    def udpipe(self) -> str:
        return f"http://{self.udpipe_host}:{self.udpipe_port}"

    def cesta_logu(self) -> str:
        return self.absolutni(self.log_soubor)

    def slozka_behu(self) -> str:
        """Kam se ukládají pid soubory a logy běžících procesů."""
        return os.path.join(self.koren, "run")

    # ---- odvozené cesty ----------------------------------------------
    def absolutni(self, cesta: str) -> str:
        return cesta if os.path.isabs(cesta) else os.path.join(self.koren, cesta)

    def slozka(self, struktura: str) -> str:
        if struktura not in PODADRESARE:
            raise KeyError(f"neznámá struktura {struktura!r}; "
                           f"znám {', '.join(sorted(PODADRESARE))}")
        return os.path.join(self.data, PODADRESARE[struktura])

    def zalozit_slozky(self) -> "Config":
        for jmeno in PODADRESARE:
            os.makedirs(self.slozka(jmeno), exist_ok=True)
        return self

    # ---- načtení ------------------------------------------------------
    @classmethod
    def nacist(cls, soubor: Optional[str] = None, **primo) -> "Config":
        hodnoty = {}
        hodnoty.update(cls._ze_souboru(soubor))
        hodnoty.update(cls._z_prostredi())
        hodnoty.update({k: v for k, v in primo.items() if v is not None})
        znama = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in hodnoty.items() if k in znama})

    @staticmethod
    def _ze_souboru(soubor: Optional[str]) -> dict:
        cesta = soubor or os.path.join(KOREN_PROJEKTU, "config.json")
        try:
            with open(cesta, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _z_prostredi() -> dict:
        out = {}
        for f in fields(Config):
            hodnota = os.environ.get(PREDPONA_ENV + f.name.upper())
            if hodnota is None:
                continue
            out[f.name] = int(hodnota) if "port" in f.name else hodnota
        return out

    def do_slovniku(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def __repr__(self) -> str:
        return (f"Config(data={self.data!r}, port={self.port}, "
                f"udpipe={self.udpipe!r})")
