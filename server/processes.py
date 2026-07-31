"""Spouštění a ukončování obou procesů: UDPipe a našeho webu.

Bez tohohle se to dělalo ručně přes nohup a pkill, a to má dvě vady: nešlo
poznat, co běží, a `pkill -f` je hrubý nástroj, který snadno sestřelí i cizí
proces s podobným řádkem. Tady má každý proces svůj pid soubor a ukončuje se
adresně.

Porty jsou 9000 (naše API) a 9010 (UDPipe) — 8000, 8001 a 8112 už na
vývojovém stroji drží jiné projekty.
"""

import errno
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass
class Proces:
    jmeno: str
    prikaz: Sequence[str]
    port: int
    slozka_behu: str
    pracovni: str
    prostredi: Optional[dict] = None

    # ---- cesty -------------------------------------------------------
    @property
    def pid_soubor(self) -> str:
        return os.path.join(self.slozka_behu, f"{self.jmeno}.pid")

    @property
    def log_soubor(self) -> str:
        return os.path.join(self.slozka_behu, f"{self.jmeno}.log")

    # ---- pid ---------------------------------------------------------
    def precist_pid(self) -> Optional[int]:
        try:
            with open(self.pid_soubor) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            return None

    def zapsat_pid(self, pid: int) -> None:
        os.makedirs(self.slozka_behu, exist_ok=True)
        with open(self.pid_soubor, "w") as f:
            f.write(str(pid))

    def zapomenout_pid(self) -> None:
        try:
            os.remove(self.pid_soubor)
        except OSError:
            pass

    # ---- stav --------------------------------------------------------
    @staticmethod
    def zije(pid: int) -> bool:
        """Signál 0 nic neudělá, jen se zeptá, jestli proces existuje."""
        try:
            os.kill(pid, 0)
        except OSError as e:
            return e.errno == errno.EPERM      # existuje, jen není náš
        return True

    def bezi(self) -> bool:
        pid = self.precist_pid()
        return bool(pid and self.zije(pid))

    def port_obsazen(self) -> bool:
        with socket.socket() as s:
            s.settimeout(0.3)
            return s.connect_ex(("127.0.0.1", self.port)) == 0

    def stav(self) -> dict:
        return {
            "jmeno": self.jmeno, "port": self.port,
            "pid": self.precist_pid(),
            "bezi": self.bezi(),
            "port_obsazen": self.port_obsazen(),
            "log": self.log_soubor,
        }

    # ---- řízení ------------------------------------------------------
    def spustit(self) -> str:
        if self.bezi():
            return f"{self.jmeno}: už běží (pid {self.precist_pid()})"
        # Cizí proces na našem portu je hlášená chyba, ne tichý pád na
        # "address already in use" schovaný v logu.
        if self.port_obsazen():
            return (f"{self.jmeno}: port {self.port} drží někdo jiný — "
                    f"uvolni ho, nebo změň port v configu")
        os.makedirs(self.slozka_behu, exist_ok=True)
        prostredi = dict(os.environ)
        prostredi.update(self.prostredi or {})
        with open(self.log_soubor, "ab") as log:
            proces = subprocess.Popen(
                self.prikaz, cwd=self.pracovni, stdout=log, stderr=log,
                stdin=subprocess.DEVNULL, env=prostredi, start_new_session=True)
        self.zapsat_pid(proces.pid)
        return f"{self.jmeno}: spuštěn (pid {proces.pid}, port {self.port})"

    def zastavit(self, cekat: float = 10.0) -> str:
        pid = self.precist_pid()
        if not pid or not self.zije(pid):
            self.zapomenout_pid()
            return f"{self.jmeno}: neběží"
        # Nejdřív slušně (SIGTERM), teprve když nereaguje, natvrdo.
        os.kill(pid, signal.SIGTERM)
        konec = time.time() + cekat
        while time.time() < konec:
            if not self.zije(pid):
                self.zapomenout_pid()
                return f"{self.jmeno}: ukončen (pid {pid})"
            time.sleep(0.2)
        os.kill(pid, signal.SIGKILL)
        self.zapomenout_pid()
        return f"{self.jmeno}: nereagoval, ukončen natvrdo (pid {pid})"

    def pockat_na_port(self, kolik: float = 90.0) -> bool:
        konec = time.time() + kolik
        while time.time() < konec:
            if self.port_obsazen():
                return True
            if not self.bezi():
                return False
            time.sleep(0.4)
        return False


class Sprava:
    """Oba procesy pohromadě. UDPipe je volitelný — bez něj web funguje,
    jen nejde rozbor vět."""

    def __init__(self, config):
        self.config = config
        beh = config.slozka_behu()
        self.udpipe = Proces(
            jmeno="udpipe",
            prikaz=[os.path.join(config.koren, "udpipe.sh")],
            port=config.udpipe_port, slozka_behu=beh, pracovni=config.koren,
            prostredi={"PORT": str(config.udpipe_port)})
        self.web = Proces(
            jmeno="web",
            prikaz=[sys.executable, "-m", "server", str(config.port)],
            port=config.port, slozka_behu=beh, pracovni=config.koren,
            prostredi={"POLE2_PORT": str(config.port)})

    def vsechny(self) -> list:
        return [self.udpipe, self.web]

    def spustit(self, co: Optional[str] = None) -> list:
        return [p.spustit() for p in self._vybrat(co)]

    def zastavit(self, co: Optional[str] = None) -> list:
        # Pozpátku: web se ukončí dřív než rozbor, na který se ptá.
        return [p.zastavit() for p in reversed(self._vybrat(co))]

    def restartovat(self, co: Optional[str] = None) -> list:
        return self.zastavit(co) + self.spustit(co)

    def stav(self) -> list:
        return [p.stav() for p in self.vsechny()]

    def _vybrat(self, co: Optional[str]) -> list:
        if not co or co == "vse":
            return self.vsechny()
        podle = {p.jmeno: p for p in self.vsechny()}
        if co not in podle:
            raise KeyError(f"znám 'udpipe', 'web' nebo 'vse', ne {co!r}")
        return [podle[co]]
