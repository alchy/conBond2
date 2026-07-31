"""Rozbor pro API — tenká slupka nad jediným klientem UDPipe v jádře.

Klienti bývali dva: tenhle a `baseline.rozebrat()`. Lišili se v tom, co
dělají se zkratkami, takže korpus mohl mít „R.U.R." rozsekané na tři tokeny
a otázka scelené — obojí by dál fungovalo a jen mluvilo o jiném slově.
Klient je teď jeden (`core.ingest.Rozbor`) a tohle k němu jen přidává, co
potřebuje HTTP: hlášení chyby místo výjimky a seznam neznámých aktivací.

Neznámé se vracejí schválně: tiše zakládat sloupce by znamenalo, že si
uživatel překlepem rozšíří atributový prostor, aniž by o tom věděl.
"""

import urllib.error

from core.ingest import Rozbor as Jadro


class Rozbor:
    def __init__(self, url, timeout=180):
        self.jadro = Jadro(url, timeout=timeout)

    def veta(self, text, zname=()):
        try:
            vety = self.jadro.rozebrat(text)
        except urllib.error.URLError as e:
            return {"chyba": "UDPipe neodpovídá (%s) — spusť ./udpipe.sh" % e.reason}
        except (ValueError, OSError) as e:
            return {"chyba": "UDPipe vrátil něco divného: %s" % e}

        tokeny = [{"form": t.form, "lemma": t.lemma.lower(), "upos": t.upos,
                   "deprel": t.deprel, "feats": list(t.feats)}
                  for v in vety for t in v]
        zname = set(zname)
        nezname = []
        if zname:
            for t in tokeny:
                for a in [t["upos"], t["deprel"]] + t["feats"]:
                    if a not in zname and a not in nezname:
                        nezname.append(a)
        return {"tokeny": tokeny, "nezname": nezname}

    def lemmata(self, text):
        try:
            return self.jadro.lemmata(text)
        except (urllib.error.URLError, ValueError, OSError):
            return None
