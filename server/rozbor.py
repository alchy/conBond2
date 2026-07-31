"""Klient k VLASTNÍ instanci UDPipe (viz udpipe.sh).

Umí jediné: poslat větu a vrátit tokeny ve tvaru, jakému rozumí pole —
{form, upos, deprel, feats[]}. CoNLL-U ven nepouštíme, ať se s ním nemusí
zabývat prohlížeč.

Model je týž, ze kterého vznikla výchozí data, takže vrácené aktivace mají
v poli obvykle už svou vertikálu. Co ji nemá, se vrací v `nezname` — tiše
zakládat sloupce by znamenalo, že si uživatel překlepem rozšíří prostor,
aniž by o tom věděl.
"""

import json
import urllib.error
import urllib.parse
import urllib.request


class Rozbor:
    def __init__(self, url, timeout=180):
        self.url = url.rstrip("/") + "/process"
        self.timeout = timeout

    def veta(self, text, zname=()):
        telo = urllib.parse.urlencode({
            "tokenizer": "", "tagger": "", "parser": "", "data": text,
        }).encode("utf-8")
        try:
            with urllib.request.urlopen(self.url, telo, timeout=self.timeout) as r:
                odpoved = json.loads(r.read().decode("utf-8"))
        except urllib.error.URLError as e:
            return {"chyba": "UDPipe neodpovídá (%s) — spusť ./udpipe.sh" % e.reason}
        except (ValueError, OSError) as e:
            return {"chyba": "UDPipe vrátil něco divného: %s" % e}

        tokeny = []
        for radek in odpoved.get("result", "").splitlines():
            if not radek or radek.startswith("#"):
                continue
            c = radek.split("\t")
            if len(c) < 8 or "-" in c[0]:      # víceslovné tokeny přeskakujeme
                continue
            feats = [] if c[5] == "_" else c[5].split("|")
            tokeny.append({
                "form": c[1], "upos": c[3], "deprel": c[7], "feats": feats,
            })

        zname = set(zname)
        nezname = []
        if zname:
            for t in tokeny:
                for a in [t["upos"], t["deprel"]] + t["feats"]:
                    if a not in zname and a not in nezname:
                        nezname.append(a)
        return {"tokeny": tokeny, "nezname": nezname}
