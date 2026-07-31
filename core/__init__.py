"""Aktivační pole — knihovna. Celý průchod bez prohlížeče.

    from core import Pole, Nastaveni, UlozisteSouboru

    pole = Pole(UlozisteSouboru("data"))
    pole.nastaveni.polomer_dotazu = 4
    pole.postavit()
    print(pole.dotazy.pocet_sablon(), "šablon dotazů")

Web je jen jeden ze dvou kanálů k témuž jádru; druhý je tenhle import.
Zdroj pravdy sedí tady, ne v prohlížeči.

Pět švů se dá vyměnit, aniž by se sáhlo do jádra — ZdrojAktivaci, Uloziste,
SkladacVektoru, Slucovac a Sitko; viz interfaces.py.
"""

from .config import PODADRESARE, Config
from .derived import (ODVOZENE, Odvozena, bez_odvozenych,  # noqa: E402
                      ocistit_korpus, vertikaly_odvozenych)
from .export import korpusy_ven, pole_ven, strana_ven
from .log import DEBUG, INFO, TICHO, Log, log, nastavit as nastavit_log
from .settings import MAX_POLOMER, Nastaveni
from .window import Okno, Slot, zapsat_offset
from .field import KORPUSY, PREDPONY, Pole
from .interfaces import Sitko, SkladacVektoru, Slucovac, Uloziste, ZdrojAktivaci
from .sieve import (SitkoStredu, SitkoStupnovane, SitkoVse,  # noqa: E402
                    filtruje_stred, jmeno_aktivace)
from .compose import Skladac, Vzor
from .lexicon import Polozka, Slovnik
from .side import Strana, Vazba
from .flow import Radek, Tok
from .storage import UlozisteSouboru
from .sources import (PRAZDNO, PRAZDNY_TVAR, SkladacRetezcem, SlucovacShodou,
                     ZdrojZTokenu)

__all__ = [
    "Pole", "Nastaveni", "UlozisteSouboru", "Config", "PODADRESARE",
    "pole_ven", "strana_ven", "korpusy_ven",
    "Odvozena", "ODVOZENE", "vertikaly_odvozenych",
    "bez_odvozenych", "ocistit_korpus",
    "log", "Log", "nastavit_log", "TICHO", "INFO", "DEBUG",
    "Tok", "Radek", "Okno", "Slot", "zapsat_offset",
    "Slovnik", "Polozka", "Strana", "Vazba",
    "Skladac", "Vzor",
    "ZdrojAktivaci", "Uloziste", "SkladacVektoru", "Slucovac", "Sitko",
    "ZdrojZTokenu", "SkladacRetezcem", "SlucovacShodou",
    "SitkoStredu", "SitkoStupnovane", "SitkoVse",
    "filtruje_stred", "jmeno_aktivace",
    "PRAZDNO", "PRAZDNY_TVAR", "MAX_POLOMER", "KORPUSY", "PREDPONY",
]
