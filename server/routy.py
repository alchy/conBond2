"""HTTP vrstva. Zná cesty a odpovědi, nezná formát dat ani rozbor —
na to má ulozne.py a rozbor.py.
"""

import json
import mimetypes
import os
import posixpath
import re
import sys
from http.server import BaseHTTPRequestHandler

STATICKE = (".html", ".css", ".js", ".json", ".svg", ".map")


def udelej_handler(koren, ulozne, rozbor):
    class Handler(BaseHTTPRequestHandler):
        server_version = "pole2/2.0"

        # ---- pomůcky ---------------------------------------------------
        def posli(self, kod, telo, typ="application/json; charset=utf-8"):
            # None je platný JSON (null) a MUSÍ se zakódovat, ne propadnout
            # dál — len(None) jinak shodí spojení a klient to vidí jako
            # "server neběží".
            if telo is None or isinstance(telo, (dict, list, bool, int, float)):
                telo = json.dumps(telo, ensure_ascii=False).encode("utf-8")
            elif isinstance(telo, str):
                telo = telo.encode("utf-8")
            self.send_response(kod)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(telo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(telo)

        def chyba(self, kod, zprava):
            self.posli(kod, {"chyba": zprava})

        def telo_json(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0:
                return None
            if n > 64 * 1024 * 1024:
                raise ValueError("tělo je příliš velké")
            return json.loads(self.rfile.read(n).decode("utf-8"))

        def log_message(self, fmt, *args):
            sys.stderr.write("  %s %s\n" % (self.command or "-", self.path))

        # ---- statické soubory ------------------------------------------
        def posli_soubor(self, rel):
            # posixpath.normpath + odstranění vedoucích ".." drží čtení
            # uvnitř kořene; bez toho by šlo požádat o /../../etc/passwd
            bezpecna = posixpath.normpath("/" + rel).lstrip("/")
            cesta = os.path.join(koren, bezpecna)
            if not os.path.isfile(cesta) or not cesta.startswith(koren):
                return self.chyba(404, "není: " + rel)
            if os.path.splitext(cesta)[1] not in STATICKE:
                return self.chyba(403, "tenhle typ souboru se neservíruje")
            typ = mimetypes.guess_type(cesta)[0] or "application/octet-stream"
            if typ.startswith("text/") or typ.endswith(("javascript", "json")):
                typ += "; charset=utf-8"
            with open(cesta, "rb") as f:
                self.posli(200, f.read(), typ)

        # ---- routy -----------------------------------------------------
        def do_GET(self):
            cesta = self.path.split("?", 1)[0]

            if cesta in ("/", "/index.html"):
                return self.posli_soubor("pole2.html")

            if cesta == "/api/state":
                if not ulozne.ma_stav():
                    # 404 = "běžím, jen tohle ještě nemám". Klient si to
                    # přeloží na "backend je, data pošlu já".
                    return self.chyba(404, "stav zatím není")
                return self.posli(200, ulozne.cti_stav())

            if cesta == "/api/maps":
                return self.posli(200, ulozne.vsechny_mapy())

            m = re.match(r"^/api/maps/([^/]+)$", cesta)
            if m:
                klic = m.group(1)
                if not ulozne.platny_klic(klic):
                    return self.chyba(400, "klíč musí být tvaru q<0-8>f<0-8>")
                if not ulozne.ma_mapu(klic):
                    return self.chyba(404, "store zatím není")
                return self.posli(200, ulozne.cti_mapu(klic))

            return self.posli_soubor(cesta.lstrip("/"))

        def do_PUT(self):
            cesta = self.path.split("?", 1)[0]
            try:
                data = self.telo_json()
            except ValueError as e:
                return self.chyba(400, "tělo není platný JSON: %s" % e)

            if cesta == "/api/state":
                if not isinstance(data, dict) or "cols" not in data:
                    return self.chyba(400, "čekám objekt s klíčem cols")
                ulozne.zapis_stav(data)
                return self.posli(200, {"ok": True})

            m = re.match(r"^/api/maps/([^/]+)$", cesta)
            if m:
                klic = m.group(1)
                if not ulozne.platny_klic(klic):
                    return self.chyba(400, "klíč musí být tvaru q<0-8>f<0-8>")
                if not isinstance(data, list):
                    return self.chyba(400, "čekám pole dvojic")
                ulozne.zapis_mapu(klic, data)
                return self.posli(200, {"ok": True, "ulozeno": len(data)})

            return self.chyba(404, "neznámá cesta")

        def do_POST(self):
            if self.path.split("?", 1)[0] != "/api/parse":
                return self.chyba(404, "neznámá cesta")
            try:
                data = self.telo_json() or {}
            except ValueError as e:
                return self.chyba(400, "tělo není platný JSON: %s" % e)
            text = (data.get("text") or "").strip()
            if not text:
                return self.chyba(400, "čekám {\"text\": \"…\"}")
            vysledek = rozbor.veta(text, zname=self.zname_aktivace())
            if "chyba" in vysledek:
                return self.chyba(502, vysledek["chyba"])
            return self.posli(200, vysledek)

        def zname_aktivace(self):
            """Vertikály, které pole zná — z uloženého stavu, jinak výchozí."""
            stav = ulozne.cti_stav() if ulozne.ma_stav() else None
            if not stav:
                try:
                    with open(os.path.join(koren, "data", "vychozi.json"),
                              encoding="utf-8") as f:
                        stav = json.load(f)
                except (OSError, ValueError):
                    return ()
            return [c["a"] for c in stav.get("cols", [])]

        def do_HEAD(self):
            self.do_GET()

    return Handler
