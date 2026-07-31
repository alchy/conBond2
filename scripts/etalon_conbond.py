#!/usr/bin/env python3
"""Etalon ze starého conBondu, projetý na tomhle korpusu.

    python3 scripts/etalon_conbond.py
    python3 scripts/etalon_conbond.py --detail
    python3 scripts/etalon_conbond.py --kind bible-fakta

PROČ ZVLÁŠŤ, A NE PŘILEPIT K NAŠEMU ETALONU. Těch 95 otázek se ptalo na JINÝ
korpus — fyziku, poznámky uživatele, účel systému. Kdyby se počítaly do
jednoho čísla s naším etalonem, klesla by úspěšnost kvůli tomu, že tu ta
data nejsou, a vypadalo by to jako vada odpovídače.

Proto se sada nejdřív ROZDĚLÍ podle toho, jestli o tom náš korpus vůbec
mluví, a měří se dvě různé věci:

    v korpusu    umíme odpovědět?          ← schopnost
    mimo korpus  umíme mlčet?              ← poctivost

Druhá půlka je cennější, než se zdá. Devadesát otázek na věci, které tu
nejsou, je zátěžová zkouška na vymýšlení: stroj, který na ně odpoví, si
vymýšlí, a to je horší než stroj, který mlčí.

TŘETÍ REŽIM, KTERÝ NEUMÍME. Starý conBond měl vedle `answer` a `unsure`
ještě `clarify` — na „Kdo byl František?" se neodpovídalo ani nemlčelo, ale
doptávalo se. To je vlastní druh odpovědi, ne varianta mlčení, a měří se tu
zvlášť.
"""

import json
import os
import sys
from collections import Counter, defaultdict

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config, Odpovidac, Pole, UlozisteSouboru, nastavit_log  # noqa: E402

SADA = os.path.join(KOREN, "data", "gold", "conbond.json")

# Kolik kandidátů se ještě počítá jako „v poli" — stejně jako v našem etalonu,
# ať jsou čísla srovnatelná.
V_POLI = 5


def sedi(text, ocekavane):
    t = (text or "").lower()
    return any(e.lower() in t for e in ocekavane)


def v_korpusu(o: Odpovidac, polozka: dict) -> bool:
    """Mluví náš korpus o tom, na co se otázka ptá?

    Měří se přes to, co se z otázky rozsvítí — ne přes jméno dokumentu,
    protože názvy zdrojů se mezi projekty neshodují. Když se nerozsvítí
    entita ani žádný obsahový tvar, korpus o tématu nemá co říct a otázka
    patří do půlky „mimo korpus"."""
    a = o.rozsvitit(polozka["q"])
    return bool(a["entita"]) or any(a["svitici"].values())


def vyhodnotit(o: Odpovidac, polozka: dict) -> dict:
    v = o.odpovedet(polozka["q"])
    kand = v["kandidati"]
    rezim = polozka.get("mode", "answer")
    if rezim == "clarify":
        # Doptání se zatím nepozná od mlčení. Počítá se jako NEsplněné, i
        # když stroj mlčí — jinak by se vlastnost, která chybí, tvářila
        # jako hotová.
        return {"ok": False, "rezim": rezim, "nalez": v,
                "duvod": "má se doptat; " + ("mlčí" if not kand
                                             else f"odpověděl {v['odpoved']!r}")}
    if rezim == "unsure" or not polozka.get("expect"):
        return {"ok": not kand, "rezim": "unsure", "nalez": v,
                "duvod": "mlčí" if not kand else f"odpověděl {v['odpoved']!r}"}
    if not kand:
        return {"ok": False, "prvni": False, "rezim": rezim, "nalez": v,
                "duvod": "mlčí, ač má odpovědět"}
    prvni = sedi(kand[0]["text"], polozka["expect"])
    v_poli = any(sedi(k["text"], polozka["expect"]) for k in kand[:V_POLI])
    return {"ok": v_poli, "prvni": prvni, "rezim": rezim, "nalez": v,
            "duvod": ("první" if prvni else
                      f"v poli ({len(kand)} kand.)" if v_poli else
                      f"mimo → {kand[0]['text']!r}")}


def tabulka(nazev, radky, sloupec):
    print(f"\n  {nazev}")
    print(f"  {'doména':<20} {'otázek':>7} {'splněno':>8} {sloupec:>8}")
    print("  " + "─" * 46)
    c = Counter()
    for kind in sorted(radky):
        k = radky[kind]
        c.update(k)
        print(f"  {kind:<20} {k['celkem']:>7} {k['ok']:>8} {k['prvni']:>8}")
    print("  " + "─" * 46)
    print(f"  {'celkem':<20} {c['celkem']:>7} {c['ok']:>8} {c['prvni']:>8}")
    if c["celkem"]:
        print(f"  → {100 * c['ok'] / c['celkem']:.0f} %")
    return c


def main() -> int:
    nastavit_log(uroven="ticho")
    pole = Pole(UlozisteSouboru(config=Config.nacist()))
    pole.nastavit_polomery(1, 1)
    pole.postavit()
    o = Odpovidac(pole)

    with open(SADA, encoding="utf-8") as f:
        sada = json.load(f)
    if "--kind" in sys.argv:
        chci = sys.argv[sys.argv.index("--kind") + 1]
        sada = [p for p in sada if p["kind"] == chci]
    detail = "--detail" in sys.argv

    doma, cizi, doptat = defaultdict(Counter), defaultdict(Counter), []
    for p in sada:
        r = vyhodnotit(o, p)
        if r["rezim"] == "clarify":
            doptat.append((p, r))
            continue
        kam = doma if v_korpusu(o, p) else cizi
        k = kam[p["kind"]]
        k["celkem"] += 1
        k["ok"] += bool(r["ok"])
        k["prvni"] += bool(r.get("prvni"))
        if detail or not r["ok"]:
            znak = "✓" if r["ok"] else "✗"
            kde = "korpus" if kam is doma else "mimo  "
            print(f"  {znak} [{kde}] {p['q']:<44} {r['duvod']}")

    a = tabulka("V KORPUSU — umíme odpovědět?", doma, "první")
    b = tabulka("MIMO KORPUS — umíme mlčet?", cizi, "—")

    print(f"\n  DOPTÁNÍ ({len(doptat)}) — vlastnost, kterou zatím nemáme")
    for p, r in doptat:
        print(f"  ✗ {p['q']:<46} {r['duvod']}")

    celkem = a["celkem"] + b["celkem"] + len(doptat)
    print(f"\n  {celkem} otázek ze starého conBondu:"
          f" v korpusu {a['ok']}/{a['celkem']}"
          f" · mimo korpus {b['ok']}/{b['celkem']}"
          f" · doptání 0/{len(doptat)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
