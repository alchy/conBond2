"""Kontrola zdraví dat — aby se tiché vady ozvaly samy.

PŘEVZATO Z conBondu (`health.py`). Tam to vzniklo z pasti „mrtvá data":
systém nad chybějícími nebo zastaralými daty tiše odpovídal „nevím" a nebylo
poznat, že se přestavba zastavila v půlce.

U nás se za jediný den staly tři takové věci a ani jedna se neohlásila:

  * styly se nenačítaly, protože se soubory přejmenovaly a odkaz zůstal starý
  * agenti se nepouštěli z přípravy a zápisem korpusu mlčky zmizeli
  * zlatá sada ukazovala na pozice vět a po přestavbě měřila jinde
    (100 % → 0 %, bez jediného varování)

Všechny tři jsou týž tvar: **A se změnilo, B o tom neví**. Tahle kontrola se
na to ptá předem.

JEN ČTE A HLÁSÍ. Nic neopravuje a nic nemění — oprava by musela hádat, co
kdo zamýšlel, a tichá oprava je horší než tichá vada.

    python3 -m core.health          # nebo Zdravi(config).zkontrolovat()
"""

import json
import os
from dataclasses import dataclass
from typing import Optional, Sequence

from .config import Config


@dataclass
class Nalez:
    """Jeden problém. `co` je krátký klíč pro strojové čtení, `proc`
    vysvětluje člověku, co se stane, když se to nechá být."""
    uroven: str          # "chyba" | "varovani"
    co: str
    proc: str

    def __str__(self) -> str:
        znak = "✗" if self.uroven == "chyba" else "!"
        return f"{znak} {self.co} — {self.proc}"


class Zdravi:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.nacist()

    # ---- jednotlivé kontroly -----------------------------------------
    def zkontrolovat(self) -> list:
        nalezy = []
        for kontrola in (self.korpus_je, self.rozbor_je_cerstvy,
                         self.agenti_probehli, self.vertikaly_pokryvaji,
                         self.zlata_sedi_na_korpus, self.styly_existuji):
            nalezy.extend(kontrola())
        return nalezy

    def korpus_je(self) -> list:
        out = []
        for jmeno, soubor in (("fakta", "facts.json"), ("dotazy", "query.json")):
            cesta = os.path.join(self.config.slozka("corpora"), soubor)
            if not os.path.exists(cesta):
                continue                  # výchozí sada se vezme z defaults
            vety = self._json(cesta)
            if vety is None:
                out.append(Nalez("chyba", f"korpus {jmeno} je poškozený",
                                 f"{cesta} nejde přečíst jako JSON"))
            elif not vety:
                out.append(Nalez("varovani", f"korpus {jmeno} je prázdný",
                                 "pole nad ním nebude mít co stavět"))
        return out

    def rozbor_je_cerstvy(self) -> list:
        """Syrový text novější než korpus = příprava neproběhla.

        Tohle je ta klasická past: přibude článek do data/raw a nikdo
        nepustí baseline. Korpus dál funguje, jen o tom článku neví."""
        raw = os.path.join(self.config.koren, "data", "raw")
        korpus = os.path.join(self.config.slozka("corpora"), "facts.json")
        if not (os.path.isdir(raw) and os.path.exists(korpus)):
            return []
        cas_korpusu = os.path.getmtime(korpus)
        novejsi = [j for j in sorted(os.listdir(raw))
                   if j.endswith(".txt")
                   and os.path.getmtime(os.path.join(raw, j)) > cas_korpusu]
        if not novejsi:
            return []
        return [Nalez("varovani", f"{len(novejsi)} článků je novějších než korpus",
                      "příprava po nich neproběhla: "
                      + ", ".join(novejsi[:3])
                      + (" …" if len(novejsi) > 3 else "")
                      + "  → python3 scripts/baseline.py vse")]

    def agenti_probehli(self) -> list:
        """Korpus bez jediné návěsky znamená, že se agenti nepustili —
        a odpovídání na „Kdy" a „Kde" pak nemá kde hledat."""
        vety = self._korpus()
        if not vety:
            return []
        navesek = sum(1 for v in vety for t in v if t.get("navesky"))
        if navesek:
            return []
        return [Nalez("chyba", "korpus nemá ani jednu návěsku agentů",
                      "otázky na čas a místo nenajdou nic "
                      "→ python3 scripts/baseline.py zapis")]

    def vertikaly_pokryvaji(self) -> list:
        """Aktivace bez sloupce v poli není vidět — a co není vidět, to se
        špatně hledá."""
        vety = self._korpus()
        cesta = os.path.join(self.config.slozka("verticals"), "verticals.json")
        cols = self._json(cesta) if os.path.exists(cesta) else None
        if not vety or cols is None:
            return []
        zname = {c["a"] for c in cols}
        chybi = {a for v in vety for t in v for a in t["acts"] if a not in zname}
        if not chybi:
            return []
        return [Nalez("varovani", f"{len(chybi)} aktivací nemá vertikálu",
                      "v poli nejsou vidět: " + ", ".join(sorted(chybi)[:5]))]

    def zlata_sedi_na_korpus(self) -> list:
        """Zlatá sada odkazuje na věty; když se korpus přestaví, musí ten
        odkaz pořád platit. Tohle je ta vada, která spadla ze 100 % na 0 %
        a nic o ní neřekla."""
        cesta = os.path.join(self.config.koren, "data", "gold", "otazky.json")
        zlata = self._json(cesta) if os.path.exists(cesta) else None
        vety = self._korpus()
        if not zlata or not vety:
            return []
        if "dok" not in zlata[0]:
            return [Nalez("chyba", "zlatá sada nemá stabilní klíč",
                          "odkazuje na pozici věty a ta přestavbu nepřežije "
                          "→ python3 scripts/otazky.py generuj")]
        kam = {(v[0].get("dok"), v[0].get("vd")) for v in vety if v}
        ztracene = sum(1 for z in zlata if (z.get("dok"), z.get("vd")) not in kam)
        if not ztracene:
            return []
        return [Nalez("varovani",
                      f"{ztracene} z {len(zlata)} zlatých otázek se v korpusu nenašlo",
                      "měří se jen zbytek → python3 scripts/otazky.py generuj")]

    def styly_existuji(self) -> list:
        """Odkaz ze stránky na soubor, který není. Přejmenování stylů to
        rozbilo a nikdo si toho nevšiml, protože stránka se dál vykreslila —
        jen bez formátování."""
        html = os.path.join(self.config.koren, "pole2.html")
        if not os.path.exists(html):
            return []
        with open(html, encoding="utf-8") as f:
            obsah = f.read()
        import re
        chybi = [c for c in re.findall(r'(?:href|src)="([^"]+\.(?:css|js))"', obsah)
                 if not os.path.exists(os.path.join(self.config.koren, c))]
        if not chybi:
            return []
        return [Nalez("chyba", f"{len(chybi)} odkazů na neexistující soubor",
                      ", ".join(chybi))]

    # ---- pomůcky -----------------------------------------------------
    @staticmethod
    def _json(cesta: str):
        try:
            with open(cesta, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def _korpus(self) -> Sequence:
        cesta = os.path.join(self.config.slozka("corpora"), "facts.json")
        return self._json(cesta) or [] if os.path.exists(cesta) else []


def zkontrolovat(config: Optional[Config] = None) -> list:
    return Zdravi(config).zkontrolovat()


def main() -> int:
    nalezy = zkontrolovat()
    if not nalezy:
        print("data vypadají zdravě")
        return 0
    for n in nalezy:
        print(n)
    return 1 if any(n.uroven == "chyba" for n in nalezy) else 0


if __name__ == "__main__":
    raise SystemExit(main())
