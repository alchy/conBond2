"""Backend: web i rozbor, se spouštěním a ukončováním.

    python3 -m server start          # nastartuje UDPipe i web
    python3 -m server stop           # ukončí oboje
    python3 -m server status
    python3 -m server restart web
    python3 -m server serve          # web na popředí (bez pid souboru)

Porty a cesty jsou v config.json, ne v kódu.
"""

import sys
from http.server import ThreadingHTTPServer

from core import Config, UlozisteSouboru, nastavit_log

from .parse import Rozbor
from core.health import zkontrolovat

from .processes import Sprava
from .routes import udelej_handler


def serve(config) -> None:
    """Web na popředí. Tohle spouští `start` na pozadí."""
    config.zalozit_slozky()
    nastavit_log(uroven=config.log_uroven, soubor=config.cesta_logu())
    uloziste = UlozisteSouboru(config=config)
    srv = ThreadingHTTPServer(("127.0.0.1", config.port),
                              udelej_handler(config, uloziste, Rozbor(config.udpipe)))
    print("pole2 běží na http://localhost:%d/" % config.port)
    print("  data   %s" % config.data)
    print("  rozbor %s" % config.udpipe)
    # Kontrola zdraví PŘED odpovídáním: tiché vady (nespuštěná příprava,
    # zlatá sada na pozicích, odkaz na přejmenovaný soubor) se jinak
    # projeví až chudšími výsledky a hledají se mnohem hůř.
    nalezy = zkontrolovat(config)
    for n in nalezy:
        print("  %s" % n)
    if not nalezy:
        print("  data   zdravá")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nkonec")
        srv.shutdown()


def vypsat_stav(sprava) -> None:
    for s in sprava.stav():
        znacka = "běží" if s["bezi"] else ("port drží někdo jiný"
                                           if s["port_obsazen"] else "neběží")
        pid = f" pid {s['pid']}" if s["pid"] else ""
        print(f"  {s['jmeno']:<7} {znacka}{pid} · port {s['port']} · {s['log']}")


def main() -> int:
    prikazy = {"start", "stop", "restart", "status", "serve"}
    argv = sys.argv[1:]
    prikaz = argv[0] if argv and argv[0] in prikazy else "serve"
    co = argv[1] if len(argv) > 1 else None

    # `python3 -m server 9000` — číslo místo příkazu je port pro serve
    port = None
    if argv and argv[0].isdigit():
        port = int(argv[0])
    config = Config.nacist(port=port)
    sprava = Sprava(config)

    if prikaz == "serve":
        serve(config)
        return 0
    try:
        radky = {"start": sprava.spustit, "stop": sprava.zastavit,
                 "restart": sprava.restartovat}.get(prikaz, lambda _: [])(co)
    except KeyError as e:
        print(e)
        return 2
    for r in radky:
        print("  " + r)
    if prikaz in ("start", "restart"):
        if sprava.web.pockat_na_port(20):
            print(f"\n  otevři http://localhost:{config.port}/")
        else:
            print("\n  web nenaběhl — koukni do run/web.log")
    if prikaz == "status" or radky:
        print()
        vypsat_stav(sprava)
    return 0


if __name__ == "__main__":
    sys.exit(main())
