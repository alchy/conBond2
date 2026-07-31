#!/usr/bin/env python3
"""Šipkový diagram krok za krokem — co se v něm děje a proč.

    python3 scripts/diagram.py

Nepotřebuje korpus ani UDPipe. Ukazuje tři věci:

  1. úlohu o věštkyni z Bartlové (kap. 4.4) i s pořadím, v jakém závěry
     vznikaly — aby bylo vidět, že se řetězí
  2. co diagram NEUDĚLÁ: z důsledku neusoudí na předpoklad a spor ohlásí
     místo aby si vybral
  3. že věci z conBondu2 do něj padají jako táž šipka — zápor z korpusu,
     naučené v dialogu i vyloučení rozměrem
"""

import os
import sys

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core.diagram import Diagram, negace  # noqa: E402

CARA = "─" * 74


def nadpis(t):
    print(f"\n{CARA}\n{t}\n{CARA}")


def vypsat_sipky(d, popis):
    print("\nŠIPKY (co bylo zadáno):")
    for z, do, duvod in d.sipky:
        print(f"    {z:>4} ⇒ {do:<4}   {duvod}")
    print("\nUZLY (každý výrok i se svou negací):")
    print("    " + " · ".join(sorted(d.uzly, key=lambda u: (u.lstrip('¬'), u))))
    if popis:
        print("\nCO ZNAMENAJÍ:")
        for k, v in popis.items():
            print(f"    {k} … {v}")


def vypsat_prubeh(r, popis=None):
    """Pořadí, v jakém uzly dostaly barvu. Slovník si drží pořadí vkládání,
    takže je z něj vidět, jak se závěry řetězily — a to je na diagramu to
    podstatné: druhý závěr je možný teprve díky prvnímu."""
    print("\nPRŮBĚH — v jakém pořadí barva vznikala:")
    krok = 0
    for u, h in r["barva"].items():
        if u.startswith("¬"):
            continue                      # negace se obarví zároveň, netiskneme
        krok += 1
        znak = "PLATÍ  " if h else "NEPLATÍ"
        jmeno = (popis or {}).get(u, "")
        print(f"    {krok}. {u} {znak}  {jmeno}")
        print(f"       ↳ {r['proc'].get(u, '')}")
    if r["neurceno"]:
        print(f"\n    NEURČENO: {', '.join(r['neurceno'])}")
    if r["spory"]:
        print("\n    SPORY:")
        for s in r["spory"]:
            print(f"       {s['uzel']}: mělo {s['mel']}, dostalo {s['dostal']}"
                  f" — {s['duvod']}")


def vestkyne():
    nadpis("1 · ÚLOHA O VĚŠTKYNI  (Bartlová, kap. 4.4)")
    popis = {"a": "věřím věštkyni", "b": "jsem hloupý",
             "c": "zaplatil jsem", "d": "dozvěděl jsem se pravdu"}
    d = (Diagram()
         .implikace("¬a", "b", "1. nevěříš-li mi, jsi hloupý")
         .implikace("b", "¬c", "2. jsi-li hloupý, nezaplatíš")
         .implikace("c", "d", "3. zaplatíš-li, dozvíš se pravdu"))
    vypsat_sipky(d, popis)
    print("\nDÁNO:  c = PLATÍ   (zaplatil jsem)")
    r = d.obarvit({"c": True})
    vypsat_prubeh(r, popis)
    print("\nODPOVĚĎ:", ", ".join(
        (popis[u] if h else "NE: " + popis[u]) for u, h in r["barva"].items()
        if not u.startswith("¬")))
    print("""
PROČ TO STOJÍ NA MODU TOLLENS. Dopředu se dá přečíst jediná šipka: c ⇒ d.
Tím by to skončilo. Že nejsem hloupý, vznikne až ZPĚTNĚ — kdybych hloupý
byl, nezaplatil bych, a já zaplatil. A teprve z toho plyne, že věštkyni
věřím. Dva ze čtyř závěrů jsou proti směru šipek.""")


def co_neudela():
    nadpis("2 · CO DIAGRAM NEUDĚLÁ")
    d = (Diagram()
         .implikace("¬a", "b", "1.").implikace("b", "¬c", "2.")
         .implikace("c", "d", "3."))

    print("\nA) Z DŮSLEDKU NEUSOUDÍ NA PŘEDPOKLAD")
    print("   dáno: d = PLATÍ  (dozvěděl jsem se pravdu)")
    r = d.obarvit({"d": True})
    print(f"   obarveno: {[u for u in r['barva'] if not u.startswith('¬')]}")
    print(f"   neurčeno: {r['neurceno']}")
    print("   ↳ „c ⇒ d\" neříká, že pravdu se dozvím JEN po zaplacení.")

    print("\nB) SPOR OHLÁSÍ, MÍSTO ABY SI VYBRAL")
    print("   dáno: c = PLATÍ a zároveň b = PLATÍ  (zaplatil jsem, a jsem hloupý)")
    r = d.obarvit({"c": True, "b": True})
    for s in r["spory"][:2]:
        print(f"   spor na {s['uzel']}: mělo {s['mel']}, dostalo {s['dostal']}")
        print(f"       původně: {s['puvodne']}")
        print(f"       teď:     {s['duvod']}")
    print("""   ↳ První verze měla u obou pravidel podmínku „a uzel ještě není
     obarvený" — a spolkla tím právě tenhle případ. Rozpor se nikde
     neprojevil a diagram vypadal, že úloha vyšla.""")


def vnuk():
    nadpis("3 · ÚLOHA O VNUKOVI — když není dáno NIC")
    JM = {"doma(jakub)": "Jakub", "doma(kačenka)": "Kačenka",
          "doma(terezka)": "Terezka"}
    print("""
ATOM NENÍ NÁLEPKA. Učebnice značí výroky j, k, t a vypadá to, že je musí
pojmenovat člověk. Nemusí: všechny tři mají týž tvar `doma(osoba)` a liší
se jen argumentem. Uzly se proto jmenují `doma(jakub)` — je to táž úloha,
jakou pole už umí, jen predikát místo šablony a osoba místo kandidáta.""")

    def uloha(prvni):
        return (Diagram().implikace(*prvni)
                .implikace("doma(kačenka)", "doma(terezka)",
                           "2. je-li Kačenka doma, je doma i Terezka")
                .implikace("¬doma(kačenka)", "doma(jakub)",
                           "3. není-li Kačenka doma, je doma Jakub"))

    for nazev, prvni in (
        ("PŮVODNÍ ZADÁNÍ", ("doma(jakub)", "¬doma(terezka)",
                            "1. je-li Jakub doma, není doma Terezka")),
        ("ZMĚNĚNÁ PRVNÍ INFORMACE", ("¬doma(jakub)", "¬doma(terezka)",
                                     "1'. není-li Jakub doma, není doma ani Terezka"))):
        d = uloha(prvni)
        print(f"\n{nazev}")
        for z, do, duvod in d.sipky:
            print(f"    {duvod}")
        r = d.obarvit({})
        print(f"\n  propagace od daného: obarveno {r['barva'] or '{}'}"
              " — nemá odkud začít")
        m = d.modely()
        print(f"  všechny bezesporné možnosti ({len(m)}):")
        for h in m:
            print("      " + " · ".join(
                f"{JM[a]} {'doma' if v else 'pryč'}" for a, v in sorted(h.items())))
        for a in sorted(JM):
            v = d.plyne(a)
            print(f"    plyne, že {JM[a]} je doma? "
                  + {True: "ANO", False: "NE", None: "nedá se rozhodnout"}[v])
        print(f"    je někdo doma vždycky? "
              + ("ANO" if all(any(h.values()) for h in m) else "ne"))
    print("""
ODPOVĚĎ: s původním zadáním se o Jakubovi rozhodnout NEDÁ — jsou dvě
možnosti a v jedné doma není. Se změněnou první informací je Jakub doma
ve všech třech, takže za vnukem jet.

A všimni si toho zvláštního na původním zadání: vynucený není ŽÁDNÝ
jednotlivý výrok, a přesto z něj něco plyne — někdo doma je vždycky.
Propagace to najít nemůže, protože nemá odkud začít. Tohle je metoda
tabulky pravdivostních hodnot (Bartlová, kap. 4.1): úplná, ale za 2^n.""")


def vecirek():
    nadpis("4 · ÚLOHA O VEČÍRKU — ekvivalence a disjunkce")
    print("""
Přibyly dvě spojky, ale ŽÁDNÝ nový druh hrany. Obojí je dvojice šipek:

    A ⇔ B    →   A ⇒ B  ·  B ⇒ A
    A ∨ B    →   ¬A ⇒ B ·  ¬B ⇒ A

U tří členů disjunkce by to už nešlo: předpoklad by musel být součin
(„není A ani B ⇒ C") a takový uzel diagram nemá. Kdo potřebuje delší,
má sáhnout po úplném rozboru.""")
    JM = {"prijde(jana)": "Jana", "prijde(pavel)": "Pavel",
          "prijde(kateřina)": "Kateřina", "prijde(vladislav)": "Vladislav",
          "prijde(lenka)": "Lenka"}
    d = (Diagram()
         .ekvivalence("prijde(jana)", "prijde(pavel)",
                      "1. Jana přijde právě tehdy, když přijde Pavel")
         .disjunkce("prijde(kateřina)", "prijde(vladislav)",
                    "2. dorazí Kateřina nebo Vladislav")
         .implikace("¬prijde(jana)", "prijde(kateřina)",
                    "3. nepřijde-li Jana, přijde Kateřina")
         .implikace("prijde(lenka)", "¬prijde(vladislav)",
                    "4. přijde-li Lenka, nepřijde Vladislav"))
    print("\nDÁNO:  Kateřina nedorazí")
    r = d.obarvit({"prijde(kateřina)": False})
    print("\nPRŮBĚH:")
    for i, (u, h) in enumerate((u, h) for u, h in r["barva"].items()
                               if not u.startswith("¬")):
        print(f"    {i + 1}. {JM[u]:<10} {'PŘIJDE' if h else 'nepřijde'}")
        print(f"       ↳ {r['proc'][u]}")
    print(f"\n    neurčeno: {r['neurceno'] or 'nic'}")
    m = d.modely({"prijde(kateřina)": False})
    print(f"    kontrola úplným rozborem: {len(m)} model, tentýž")
    print("\nODPOVĚĎ: na večírku budou " + ", ".join(
        JM[u] for u, h in r["barva"].items() if h and not u.startswith("¬")))


def z_conbondu():
    nadpis("5 · VĚCI Z conBondu2 JSOU TÁŽ ŠIPKA")
    print("""
Nic z toho není nová větev v kódu. Všechno jsou implikace, jen z jiného
zdroje — a v důvodu je vidět odkud.""")
    popis = {"realistka": "Němcová je realistka",
             "romantička": "Němcová je romantička",
             "znal_halmana": "Němcová znala Halmana",
             "zila_s_halmanem": "žili ve stejné době"}
    d = (Diagram()
         # zápor z KORPUSU — agent Druh dal `Typ=druh_ne`
         .implikace("realistka", "¬romantička",
                    "korpus: proudy se vylučují")
         # pravidlo naučené z FAKTŮ — indukce nad hranami
         .implikace("znal_halmana", "zila_s_halmanem",
                    "pravidlo z faktů: znal ⇒ byli současníci")
         # vyloučení ROZMĚREM — čas, změřený na doložených dvojicích
         .implikace("zila_s_halmanem", "¬disjunktni_intervaly",
                    "rozměr čas: značka `disjunktni` se u doložených nevyskytla"))
    vypsat_sipky(d, popis)
    print("\nDÁNO:  disjunktni_intervaly = PLATÍ")
    print("       (Němcová †1862, Halman *1873 — osa čas)")
    r = d.obarvit({"disjunktni_intervaly": True})
    vypsat_prubeh(r, popis)
    print("""
ODPOVĚĎ: Němcová Halmana znát NEMOHLA — a je vidět celý řetěz:
    disjunktní intervaly  ⇒  nežili současně  ⇒  neznali se

Každý krok má jiný původ (rozměr, naučené pravidlo, korpus) a diagram
je nerozlišuje. To je celý smysl: vyhledání, odvození i vyloučení jsou
jedna operace.""")


def main():
    vestkyne()
    co_neudela()
    vnuk()
    vecirek()
    z_conbondu()
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
