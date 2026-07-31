"""HTTP vrstva. Tenká: zná cesty a odpovědi, nic nepočítá — počítá core/.

Frontend je jeden ze dvou kanálů k témuž jádru; druhý je `import core`.
Zdroj pravdy sedí tady na backendu, prohlížeč si model jen vyzvedne.
"""

import json
import mimetypes
import os
import posixpath
import re
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from core import (CELY, Pole, Skladac, Vyrez, korpusy_ven, log,
                  pole_ven, prehled_sablon)
from core.derived import bez_odvozenych, ocistit_korpus
from core.dialog import Rozhovor
from core.tvrzeni import INSTANCE, PODTRIDA, Mluvnice, Znalost
from core.window import Okno

STATICKE = (".html", ".css", ".js", ".json", ".svg", ".map")
PRAVDA = ("1", "true", "ano")


def udelej_lemmatizator(rozbor):
    """Pojmy z dialogu se lemmatizují týmž UDPipe jako věty. Pamatuje si,
    co už viděl — v rozhovoru se stejné slovo opakuje pořád dokola. Bez
    UDPipe se jen zmenší písmena, ať se dá pracovat i tak."""
    pamet = {}

    def lemmatizuj(text: str) -> str:
        klic = (text or "").strip().lower()
        if not klic:
            return klic
        if klic not in pamet:
            pamet[klic] = rozbor.lemmata(text) or klic
        return pamet[klic]

    return lemmatizuj


def udelej_handler(config, uloziste, rozbor):
    pole = Pole(uloziste)
    # Rozhovor žije po celou dobu běhu serveru; tvrzení se ukládají hned,
    # takže restart o nic nepřijde.
    znalost = Znalost(config.cesta_znalosti())
    znalost.naplnit_ze_svazu(config.cesta_svazu())
    rozhovor = Rozhovor(znalost, Mluvnice(udelej_lemmatizator(rozbor)))

    class Handler(BaseHTTPRequestHandler):
        server_version = "pole2/3.0"

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

        def parametry(self):
            return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

        def cele(self, q, klic, vychozi=None):
            try:
                return int(q[klic])
            except (KeyError, TypeError, ValueError):
                return vychozi

        def vyrezy(self, q):
            """Kolik vět poslat. Pole se staví celé; tohle je jen okno, kterým
            se do něj kouká — spisovatelský korpus má 59 106 řádků a prohlížeč
            z toho neudělá nic."""
            vet = self.cele(q, "vety")
            if vet is None or vet <= 0:
                return {"f": CELY, "q": CELY}
            od = max(0, self.cele(q, "odvety", 0) or 0)
            return {"f": Vyrez(od, vet), "q": Vyrez(od, vet)}

        def log_message(self, fmt, *args):
            sys.stderr.write("  %s %s\n" % (self.command or "-", self.path))

        # ---- nastavení z dotazu ----------------------------------------
        def nastavit_pole(self, q):
            """Poloměr se nastaví jednou a platí; setter jen poznamená, že
            model zestaral, přepočítá se až při postavit()."""
            n = pole.nastaveni
            if "rf" in q:
                n.polomer_faktu = int(q["rf"])
            if "rq" in q:
                n.polomer_dotazu = int(q["rq"])
            if "syrove" in q:
                n.syrove = q["syrove"] in PRAVDA
            if "stred" in q:
                n.stred_uvnitr = q["stred"] in PRAVDA
            if "stred_atr" in q:
                # čárkami oddělený seznam; prázdný = celý střed
                n.stred_atributy = q["stred_atr"]
            if "typy" in q:
                n.typy = q["typy"] in PRAVDA
            return n

        # ---- statické soubory ------------------------------------------
        def posli_soubor(self, rel):
            # normpath + odstranění vedoucích ".." drží čtení uvnitř kořene;
            # bez toho by šlo požádat o /../../etc/passwd
            bezpecna = posixpath.normpath("/" + rel).lstrip("/")
            cesta = os.path.join(config.koren, bezpecna)
            if not os.path.isfile(cesta) or not cesta.startswith(config.koren):
                return self.chyba(404, "není: " + rel)
            if os.path.splitext(cesta)[1] not in STATICKE:
                return self.chyba(403, "tenhle typ souboru se neservíruje")
            typ = mimetypes.guess_type(cesta)[0] or "application/octet-stream"
            if typ.startswith("text/") or typ.endswith(("javascript", "json")):
                typ += "; charset=utf-8"
            with open(cesta, "rb") as f:
                self.posli(200, f.read(), typ)

        # ---- GET -------------------------------------------------------
        def do_GET(self):
            cesta = self.path.split("?", 1)[0]
            q = self.parametry()

            if cesta in ("/", "/index.html"):
                return self.posli_soubor("pole2.html")

            if cesta == "/api/field":
                self.nastavit_pole(q)
                return self.posli(200, pole_ven(
                    pole, s_korpusy=q.get("korpusy") in PRAVDA,
                    vyrezy=self.vyrezy(q)))

            if cesta == "/api/templates":
                # Vzory samy o sobě — pohled, který velký korpus unese.
                self.nastavit_pole(q)
                pole.postavit()
                strana = pole.strana("q" if q.get("strana") == "q" else "f")
                return self.posli(200, prehled_sablon(
                    strana, od=max(0, self.cele(q, "od", 0) or 0),
                    pocet=min(200, max(1, self.cele(q, "pocet", 60) or 60)),
                    razeni=q.get("razeni", "velikost"),
                    hledat=(q.get("hledat") or "").strip().lower()))

            if cesta == "/api/data":
                # Týž katalog i tytéž věty jako /api/field — tedy i s hrubými
                # vrstvami. Kdyby se to lišilo, mřížka by podle toho, kterou
                # cestou se data načetla, ukazovala jednou o tři sloupce míň.
                pole.postavit()
                vyrezy = self.vyrezy(q)
                return self.posli(200, {
                    "vertikaly": pole.vypsat_vertikaly(),
                    "korpusy": korpusy_ven(pole, vyrezy),
                    "vyrez": {"od_vety": vyrezy["f"].od_vety,
                              "vet": vyrezy["f"].vet},
                    "celkem": {jm: len(uloziste.nacist_korpus(jm))
                               for jm in ("facts", "query")},
                })

            if cesta == "/api/dialog":
                return self.posli(200, rozhovor.vypsat_stav())

            if cesta == "/api/mappings":
                return self.posli(200, uloziste.vypsat_mapovani())

            m = re.match(r"^/api/mappings/([^/]+)$", cesta)
            if m:
                try:
                    klic = uloziste.overit_klic(m.group(1))
                except ValueError as e:
                    return self.chyba(400, str(e))
                # Store pro tuhle dvojici poloměrů ještě nemusí existovat;
                # úložiště v tom případě vrátí výchozí sadu. Dřív se tu
                # vracela 404 a prohlížeč si zakládal PRÁZDNÉ mapování,
                # takže se předvyplněné dvojice ztratily.
                return self.posli(200, {
                    "dvojice": uloziste.nacist_mapovani(klic),
                    "vlastni": uloziste.ma_mapovani(klic),
                })

            return self.posli_soubor(cesta.lstrip("/"))

        # ---- PUT -------------------------------------------------------
        def do_PUT(self):
            cesta = self.path.split("?", 1)[0]
            try:
                data = self.telo_json()
            except ValueError as e:
                return self.chyba(400, "tělo není platný JSON: %s" % e)

            if cesta == "/api/data":
                if not isinstance(data, dict) or "vertikaly" not in data:
                    return self.chyba(400, "čekám objekt s klíčem vertikaly")
                # Hrubé vrstvy prohlížeč dostal, aby je uměl vykreslit, ale
                # zpátky se neukládají — počítají se z jemných.
                uloziste.ulozit_vertikaly(bez_odvozenych(data["vertikaly"]))
                for jm in ("facts", "query"):
                    if jm in data.get("korpusy", {}):
                        uloziste.ulozit_korpus(jm, ocistit_korpus(data["korpusy"][jm]))
                pole.zapomenout_katalog()           # data se změnila, přepočítat
                return self.posli(200, {"ok": True})

            m = re.match(r"^/api/mappings/([^/]+)$", cesta)
            if m:
                try:
                    klic = uloziste.overit_klic(m.group(1))
                except ValueError as e:
                    return self.chyba(400, str(e))
                if not isinstance(data, list):
                    return self.chyba(400, "čekám pole dvojic")
                uloziste.ulozit_mapovani(klic, data)
                return self.posli(200, {"ok": True, "ulozeno": len(data)})

            return self.chyba(404, "neznámá cesta")

        # ---- POST ------------------------------------------------------
        def do_POST(self):
            cesta = self.path.split("?", 1)[0]
            try:
                data = self.telo_json() or {}
            except ValueError as e:
                return self.chyba(400, "tělo není platný JSON: %s" % e)

            if cesta == "/api/parse":
                text = (data.get("text") or "").strip()
                if not text:
                    return self.chyba(400, 'čekám {"text": "…"}')
                zname = [c["a"] for c in uloziste.nacist_vertikaly()]
                vysledek = rozbor.veta(text, zname=zname)
                if "chyba" in vysledek:
                    return self.chyba(502, vysledek["chyba"])
                return self.posli(200, vysledek)

            if cesta == "/api/compose":
                return self.posli(200, self.slozit(data))

            # Dialog: text dovnitř, celý stav ven. Prohlížeč si nic nedopočítává
            # — o tom, co se s větou stalo, rozhoduje jádro.
            if cesta == "/api/dialog":
                rozhovor.poslat(data.get("text") or "")
                return self.posli(200, rozhovor.vypsat_stav())

            if cesta == "/api/dialog/decide":
                volba = data.get("druh")
                if volba == "preskocit":
                    rozhovor.preskocit()
                elif volba in (PODTRIDA, INSTANCE):
                    rozhovor.rozhodnout(volba)
                else:
                    return self.chyba(400, "druh je podtrida, instance nebo preskocit")
                return self.posli(200, rozhovor.vypsat_stav())

            if cesta == "/api/dialog/forget":
                rozhovor.zapomenout()
                return self.posli(200, rozhovor.vypsat_stav())

            return self.chyba(404, "neznámá cesta")

        def slozit(self, data):
            """Vektor složené otázky. Skládá ho jádro, ne prohlížeč —
            aktivace se berou ze slovníku a je to týž kód jako pro věty."""
            self.nastavit_pole(self.parametry())
            pole.postavit()
            skladac = Skladac(pole.ziskat_slovnik(), pole.zdroj, pole.skladac,
                              Okno(pole.nastaveni.polomer_dotazu,
                                   pole.nastaveni.stred_uvnitr),
                              pole.sitko)
            skladac.vzor.slova = list(data.get("q", []))
            skladac.vzor.kotva = int(data.get("kotva", -1))
            skladac.vzor.cile = list(data.get("f", []))
            slozeno = skladac.slozit_vektor()
            return {
                "vektor": pole.skladac.vypsat_vektor(slozeno["vektor"]),
                "mimo_okno": slozeno["mimo_okno"],
                "nezname": slozeno["nezname"],
                "nejiste": slozeno["nejiste"],
                "offsety": [[t, d] for t, d in skladac.spocitat_offsety()],
                "shoda": skladac.najit_shodnou_sablonu(
                    slozeno["vektor"], pole.dotazy.vypsat_sablony()),
                "hotovy": skladac.vzor.je_hotovy(),
            }

        def do_HEAD(self):
            self.do_GET()

    return Handler
