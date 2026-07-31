"""Spuštění backendu.

    python3 -m server            # port 8000, UDPipe na 8020
    PORT=9000 python3 -m server

Sám nic neumí — jen složí úložné, rozbor a routy dohromady.
"""

import os
import sys
from http.server import ThreadingHTTPServer

from .rozbor import Rozbor
from .routy import udelej_handler
from .ulozne import Ulozne

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    port = int(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PORT", 8000))
    udpipe = os.environ.get("UDPIPE_URL", "http://127.0.0.1:8020")

    ulozne = Ulozne(KOREN)
    rozbor = Rozbor(udpipe)
    srv = ThreadingHTTPServer(("127.0.0.1", port), udelej_handler(KOREN, ulozne, rozbor))

    print("pole2 běží na http://localhost:%d/" % port)
    print("  data   %s" % ulozne.data)
    print("  rozbor %s  (spusť ./udpipe.sh)" % udpipe)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nkonec")
        srv.shutdown()


if __name__ == "__main__":
    main()
