"""Log. Dvě úrovně a obě mají jiný účel.

INFO je lehké: že průchod probíhá a kudy. Pár řádků na průchod, dá se
nechat zapnuté pořád.

DEBUG říká co, jak, ve které metodě a s jakým výsledkem. Je rozsáhlý
schválně — smyslem je, aby se na ten výstup dalo pověsit a chování programu
se dalo číst zpětně, aniž by se do něj muselo znovu sahat. Jméno metody se
doplňuje samo ze zásobníku volání, takže se v hlášce nemusí opakovat a
nemůže se rozejít s tím, kde skutečně je.

Píše se na konzoli i do souboru, obojí volitelně:

    from core.log import log, nastavit
    nastavit(uroven="debug", soubor="run/core.log")
    log.info("stavím pole", r_f=1, r_q=4)
    with log.krok("slovník"):
        ...
"""

import inspect
import os
import sys
import time
from contextlib import contextmanager
from typing import Optional, TextIO

TICHO, INFO, DEBUG = 0, 1, 2
UROVNE = {"ticho": TICHO, "info": INFO, "debug": DEBUG}
NAZVY = {TICHO: "TICHO", INFO: "INFO", DEBUG: "DEBUG"}


def _kde(hloubka: int = 3) -> str:
    """Modul a metoda, odkud se loguje. Bere se ze zásobníku, ne z parametru
    — psát to ručně znamená, že se to dřív nebo později rozejde."""
    try:
        ramec = inspect.stack()[hloubka]
    except IndexError:
        return "?"
    modul = inspect.getmodulename(ramec.filename) or "?"
    jmeno = ramec.function
    trida = ""
    ja = ramec.frame.f_locals.get("self")
    if ja is not None:
        trida = type(ja).__name__ + "."
    return f"{modul}.{trida}{jmeno}"


def _udaje(kw: dict) -> str:
    if not kw:
        return ""
    kusy = []
    for k, v in kw.items():
        if isinstance(v, float):
            v = f"{v:.3f}"
        elif isinstance(v, (list, tuple, set)) and len(v) > 6:
            v = f"[{len(v)} položek]"
        kusy.append(f"{k}={v}")
    return "  " + " ".join(kusy)


class Log:
    def __init__(self, uroven: int = INFO, soubor: Optional[str] = None,
                 konzole: bool = True):
        self.uroven = uroven
        self.konzole = konzole
        self._soubor: Optional[TextIO] = None
        self.otevrit(soubor)

    # ---- nastavení ---------------------------------------------------
    def otevrit(self, soubor: Optional[str]) -> "Log":
        self.zavrit()
        if soubor:
            os.makedirs(os.path.dirname(os.path.abspath(soubor)), exist_ok=True)
            self._soubor = open(soubor, "a", encoding="utf-8", buffering=1)
        return self

    def zavrit(self) -> None:
        if self._soubor:
            self._soubor.close()
            self._soubor = None

    def nastavit_uroven(self, uroven) -> "Log":
        if isinstance(uroven, str):
            if uroven not in UROVNE:
                raise ValueError(f"úroveň je {', '.join(UROVNE)}, ne {uroven!r}")
            uroven = UROVNE[uroven]
        self.uroven = uroven
        return self

    def ziskat_uroven(self) -> str:
        return NAZVY[self.uroven].lower()

    def zapnuty(self, uroven: int) -> bool:
        return self.uroven >= uroven

    # ---- psaní -------------------------------------------------------
    def _radek(self, uroven: int, zprava: str, kw: dict, hloubka: int = 3) -> None:
        if not self.zapnuty(uroven):
            return
        cas = time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"
        kde = _kde(hloubka) if uroven == DEBUG else ""
        radek = f"{cas} {NAZVY[uroven]:<5} {kde + '  ' if kde else ''}{zprava}{_udaje(kw)}"
        if self.konzole:
            print(radek, file=sys.stderr)
        if self._soubor:
            self._soubor.write(radek + "\n")

    def info(self, zprava: str, **kw) -> None:
        """Že průchod probíhá a kudy. Lehké, pár řádků na průchod."""
        self._radek(INFO, zprava, kw)

    def debug(self, zprava: str, **kw) -> None:
        """Co, jak, ve které metodě a s jakým výsledkem."""
        self._radek(DEBUG, zprava, kw)

    @contextmanager
    def krok(self, nazev: str, **kw):
        """Ohraničí fázi průchodu a změří ji. Konec se hlásí i při výjimce,
        jinak by se v logu ztratilo, kde to spadlo."""
        zacatek = time.perf_counter()
        self._radek(INFO, f"› {nazev}", kw, hloubka=4)
        try:
            yield self
        except Exception as e:
            ms = (time.perf_counter() - zacatek) * 1000
            self._radek(INFO, f"✗ {nazev}", {"ms": ms, "chyba": e}, hloubka=4)
            raise
        else:
            ms = (time.perf_counter() - zacatek) * 1000
            self._radek(INFO, f"‹ {nazev}", {"ms": ms}, hloubka=4)


log = Log()


def nastavit(uroven=None, soubor: Optional[str] = None,
             konzole: Optional[bool] = None) -> Log:
    """Přenastaví společný log. Volá se jednou při startu."""
    if uroven is not None:
        log.nastavit_uroven(uroven)
    if soubor is not None:
        log.otevrit(soubor)
    if konzole is not None:
        log.konzole = konzole
    return log
