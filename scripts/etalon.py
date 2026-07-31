#!/usr/bin/env python3
"""Kurátorovaná sada otázek — psaná rukou, ne generovaná.

    python3 scripts/etalon.py              # skóre
    python3 scripts/etalon.py --detail     # každá otázka zvlášť
    python3 scripts/etalon.py --kind bible # jen jedna doména

PROČ VEDLE GENEROVANÉ SADY. Těch 682 otázek z `otazky.py` má odpověď
Z KONSTRUKCE — vznikly z návěsek, které v korpusu leží. Měří se jimi, jestli
je systém najde, ne jestli umí odpovídat. Nikdy se z nich nedozvíme:

  * co se stane u otázky, kterou by položil člověk („Kolik zubů má pes?")
  * jestli systém pozná, že NEVÍ
  * jestli to funguje i mimo tvar „Kdy/Kde <sloveso> <jméno>?"

TVAR POLOŽKY, převzatý z etalonu conBondu:

    q       otázka tak, jak by ji napsal člověk
    expect  co musí být v odpovědi; SEZNAM podřetězců, ne přesný úsek
    mode    "answer" = má odpovědět · "unsure" = má MLČET
    kind    doména, ať je vidět, kde to drhne
    dok     odkud to je — kvůli kontrole, že fakt v korpusu opravdu je

PODŘETĚZCE, NE PŘESNÁ SHODA. Odpověď je úsek textu v pádu, jaký si žádá věta
(„v Židenicích"), a trvat na hranici úseku znamená měřit tokenizaci, ne
odpověď.

MLČENÍ SE POČÍTÁ. Stroj, který si vymyslí, je horší než stroj, který mlčí —
proto je `unsure` plnohodnotný režim a ne poznámka pod čarou.
"""

import json
import os
import sys
from collections import Counter, defaultdict

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import Config, Odpovidac, Pole, UlozisteSouboru, nastavit_log  # noqa: E402


SCENARE = [
    # Nález z dialogu: naučená hrana se na „Kdo je?" vůbec neuplatnila.
    # Odpovídač čte pole, znalost leží vedle, a člověk to řekl před vteřinou.
    {"nazev": "naučené vítězí nad korpusem",
     "kroky": [("Božena Němcová je spisovatelka.", ["přijato"]),
               ("Kdo je Božena Němcová?", ["spisovatelka"])]},
    # Doptání je vlastní druh tahu, ne varianta mlčení.
    {"nazev": "shodné jméno se nehádá",
     "kroky": [("Kdo je Novák?", ["upřesni"])]},
]


def scenare(odpovidac) -> tuple:
    """Vícetahové zkoušky. Některé vlastnosti se JEDNOU otázkou změřit
    nedají: že naučené vítězí nad korpusem, je vidět až tehdy, když se
    systém nejdřív něco naučí. Etalon má jinak každou otázku samostatně,
    schválně — tohle je výjimka a je pojmenovaná."""
    ok = spatne = 0
    for s in SCENARE:
        r = Rozhovor(Znalost(), odpovidac=odpovidac)
        chyby = []
        for veta, ceka in s["kroky"]:
            z = r.poslat(veta)
            odp = (z.nalez or {}).get("odpoved") or z.odpoved or ""
            if not any(c.lower() in odp.lower() for c in ceka):
                chyby.append(f"{veta!r} → {odp!r}, čekáno {ceka}")
        if chyby:
            spatne += 1
            print(f"  ✗ scénář „{s['nazev']}\"")
            for c in chyby:
                print(f"      {c}")
        else:
            ok += 1
    return ok, spatne


def brana(odp, polozky):
    """Projde otázka vůbec do pole? Odpovídač se dá zavolat napřímo, ale
    dialog se nejdřív ptá `je_na_obsah()` — a co tam neprojde, na to se
    člověk odpovědi nedočká, i kdyby ji pole mělo."""
    return [p["q"] for p in polozky if not odp.je_na_obsah(p["q"])]
from core.dialog import Rozhovor  # noqa: E402
from core.tvrzeni import Znalost  # noqa: E402

SADA = os.path.join(KOREN, "data", "gold", "etalon.json")
# Kolik kandidátů se ještě počítá jako „v poli". Šablona neidentifikuje jednu
# odpověď, ale druh místa — proto se měří obojí: první i v poli.
V_POLI = 5


def nacist():
    with open(SADA, encoding="utf-8") as f:
        return json.load(f)


def sedi(text: str, ocekavane) -> bool:
    t = (text or "").lower()
    return any(e.lower() in t for e in ocekavane)


def vyhodnotit(o: Odpovidac, polozka: dict, rozhovor=None) -> dict:
    """`navazuje` znamená, že otázka patří k PŘEDCHOZÍ — jde týmž rozhovorem,
    aby se uplatnilo téma. Ostatní se ptají samostatně, ať výsledek nezávisí
    na pořadí; to je celý smysl etalonu."""
    if polozka.get("navazuje") and rozhovor is not None:
        z = rozhovor.poslat(polozka["q"])
        v = z.nalez or {"kandidati": [], "odpoved": None,
                        "aktivace": {}, "typ": None, "vet": 0}
    else:
        v = o.odpovedet(polozka["q"])
    kand = v["kandidati"]
    if polozka["mode"] == "unsure":
        return {"ok": not kand, "duvod": "mlčí" if not kand
                else f"odpověděl {v['odpoved']!r}", "nalez": v}
    if not kand:
        return {"ok": False, "prvni": False, "duvod": "mlčí, ač má odpovědět",
                "nalez": v}
    prvni = sedi(kand[0]["text"], polozka["expect"])
    v_poli = any(sedi(k["text"], polozka["expect"]) for k in kand[:V_POLI])
    return {"ok": v_poli, "prvni": prvni, "nalez": v,
            "duvod": ("první" if prvni else
                      f"v poli ({len(kand)} kand.)" if v_poli else
                      f"mimo → {kand[0]['text']!r}")}


def main() -> int:
    nastavit_log(uroven="ticho")
    pole = Pole(UlozisteSouboru(config=Config.nacist()))
    pole.nastavit_polomery(1, 1)
    pole.postavit()
    o = Odpovidac(pole)
    sada = nacist()
    if "--kind" in sys.argv:
        chci = sys.argv[sys.argv.index("--kind") + 1]
        sada = [p for p in sada if p["kind"] == chci]

    podle_kind = defaultdict(lambda: Counter())
    detail = "--detail" in sys.argv
    rozhovor = Rozhovor(Znalost(), odpovidac=o)
    for p in sada:
        if not p.get("navazuje"):
            # nový řetěz: téma z předchozí otázky se nesmí přelít
            rozhovor = Rozhovor(Znalost(), odpovidac=o)
            rozhovor.poslat(p["q"])
        r = vyhodnotit(o, p, rozhovor)
        k = podle_kind[p["kind"]]
        k["celkem"] += 1
        k["ok"] += bool(r["ok"])
        k["prvni"] += bool(r.get("prvni"))
        if p["mode"] == "unsure":
            k["unsure"] += 1
        if detail or not r["ok"]:
            znak = "✓" if r["ok"] else "✗"
            print(f"  {znak} {p['q']:<48} {r['duvod']}")
            if not r["ok"] and p["mode"] == "answer":
                print(f"      čekáno: {', '.join(p['expect'])}")

    print(f"\n  {'doména':<18} {'otázek':>7} {'uspěl':>7} {'první':>7}"
          f" {'z toho mlčet':>13}")
    print("  " + "─" * 58)
    c = Counter()
    for kind in sorted(podle_kind):
        k = podle_kind[kind]
        c.update(k)
        print(f"  {kind:<18} {k['celkem']:>7} {k['ok']:>7} {k['prvni']:>7}"
              f" {k['unsure']:>13}")
    print("  " + "─" * 58)
    print(f"  {'celkem':<18} {c['celkem']:>7} {c['ok']:>7} {c['prvni']:>7}"
          f" {c['unsure']:>13}")
    s_ok, s_spatne = scenare(o)
    print(f"\n  scénáře: {s_ok}/{s_ok + s_spatne} prošlo")
    mimo = brana(o, sada)
    if mimo:
        print(f"\n  POZOR: {len(mimo)} otázek neprojde branou do pole:")
        for q in mimo:
            print(f"    {q}")
    if c["celkem"]:
        print(f"\n  uspěl {100*c['ok']/c['celkem']:.0f} %"
              f" · první {100*c['prvni']/max(1, c['celkem']-c['unsure']):.0f} %"
              f" (z odpovídaných)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
