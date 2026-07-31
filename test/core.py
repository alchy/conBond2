"""Testy jádra. Bez prohlížeče, bez serveru — jen import knihovny.

    python3 test/core.py
    python3 test/core.py --debug      # i s trasováním z logu
"""

import os
import shutil
import sys
import tempfile

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOREN)

from core import (Config, Nastaveni, Pole, SitkoStredu,  # noqa: E402
                  SitkoStupnovane, SitkoVse, Skladac, UlozisteSouboru,
                  ZdrojZTokenu, filtruje_stred, korpusy_ven, nastavit_log,
                  pole_ven, vertikaly_odvozenych)
from core.compose import popsat_zaznam  # noqa: E402
from core.window import Okno  # noqa: E402

chyb = 0


def ok(podminka, zprava):
    global chyb
    if not podminka:
        chyb += 1
        print("  ✗ " + zprava)


# Testy měří proti VÝCHOZÍ sadě, ne proti pracovní kopii. První verze brala
# Config.nacist(), takže jakmile se do data/corpora/ nahrál baseline korpus,
# začala tvrdit čísla z jiných dat, než na kterých běžela. Přesně na tohle
# je Config: ukáže se na jinou složku, kde jsou jen defaults, a úložiště si
# je vezme, protože pracovní kopie chybí.
_DOCASNA = tempfile.mkdtemp(prefix="pole2-test-")
shutil.copytree(os.path.join(KOREN, "data", "defaults"),
                os.path.join(_DOCASNA, "defaults"))
CONFIG = Config(data=_DOCASNA)


def nove_pole(**kw):
    pole = Pole(UlozisteSouboru(config=CONFIG))
    for klic, hodnota in kw.items():
        setattr(pole.nastaveni, klic, hodnota)
    return pole.postavit()


print("— odsazení drží hranice vět, oba korpusy, r 0–8 —")
print("r | fakta: řádků/středů/šablon | dotazy: řádků/středů/šablon | mimo | přes")
for r in range(9):
    pole = nove_pole(polomer_faktu=r, polomer_dotazu=r)
    mimo = pres = 0
    for k in ("f", "q"):
        strana = pole.strana(k)
        for i, sloty in strana.sloty_radku.items():
            for sl in sloty:
                radek = strana.tok.radek(sl.j)
                if radek is None:
                    mimo += 1
                elif radek.veta != strana.tok.radky[i].veta:
                    pres += 1
    f, q = pole.fakta, pole.dotazy
    print(f"{r} | {f.tok.pocet_radku()}/{f.pocet_stredu()}/{f.pocet_sablon()}"
          f" | {q.tok.pocet_radku()}/{q.pocet_stredu()}/{q.pocet_sablon()}"
          f" | {mimo} | {pres}")
    ok(mimo == 0, f"r={r}: {mimo} slotů míří mimo pole")
    ok(pres == 0, f"r={r}: {pres} slotů přelezlo do sousední věty")
    ok(f.pocet_stredu() == 75, f"r={r}: středů faktů {f.pocet_stredu()}, čekáno 75")
    ok(q.pocet_stredu() == 260, f"r={r}: středů dotazů {q.pocet_stredu()}, čekáno 260")
    ma_prazdno = pole.ziskat_slovnik().najit("<empty>") is not None
    ok(ma_prazdno == (r > 0), f"r={r}: <empty> ve slovníku = {ma_prazdno}")

print("\n— poloměry se smí lišit a nastaví se jednou —")
pole = nove_pole(polomer_faktu=1, polomer_dotazu=4)
print(f"  fakta r=1 → {pole.fakta.pocet_sablon()} šablon"
      f" · dotazy r=4 → {pole.dotazy.pocet_sablon()} šablon")
ok(Okno(1, False).pocet_slotu() == 2 and Okno(4, False).pocet_slotu() == 8,
   "počet slotů se neliší podle poloměru")
ok(pole.ziskat_klic_mapovani() == "q4f1", "klíč mapování nesedí s poloměry")
n = Nastaveni()
n.polomer_dotazu = 3
ok(n.zestaralo, "setter neoznačil model za zestaralý")
n.oznacit_cerstvym()
n.polomer_dotazu = 3
ok(not n.zestaralo, "nastavení téže hodnoty zbytečně zneplatnilo model")

print("\n— slovník je společný, šablony a vazby ne —")
pole = nove_pole()
s = pole.ziskat_slovnik()
v_obou = s.vypsat_tvary_v_obou()
print(f"  slovník {len(s)} · v obou {len(v_obou)} · nejistých {len(s.vypsat_nejiste())}")
print(f"  vazby: fakta {len(pole.fakta.vazby)} · dotazy {len(pole.dotazy.vazby)}")
ok(len(s) == 104, f"slovník {len(s)}, čekáno 104")
ok(len(v_obou) == 38, f"v obou {len(v_obou)}, čekáno 38")
ok(pole.fakta.pocet_sablon() == 71 and pole.dotazy.pocet_sablon() == 161,
   "počty šablon nesedí")
ok(len(pole.fakta.vazby) == 74 and len(pole.dotazy.vazby) == 210,
   "počty vazeb nesedí")
for k, predpona in (("f", "t"), ("q", "q")):
    strana = pole.strana(k)
    zpet = sum(len(strana.vypsat_vazby_sablony(t)) for t in strana.vypsat_sablony())
    ok(zpet == len(strana.vazby),
       f"{k}: zpětných odkazů {zpet}, vazeb {len(strana.vazby)}")
    ok(all(t.startswith(predpona) for t in strana.vypsat_sablony()),
       f"{k}: šablony nemají předponu {predpona}")

print("\n— vypnutý významový typ nesmí Typ= pustit do vektoru —")
pole = nove_pole(typy=False)
prosaklo = [a for info in pole.fakta.vypsat_sablony().values()
            for a in info["vec"] if ":Typ=" in a]
print("  slotů s Typ=:", len(prosaklo))
ok(not prosaklo, "Typ= prosáklo do vektoru i při vypnutém přepínači")

print("\n— tázací tvar rozděluje to, co UD slévá —")
pole = nove_pole()
kolidujici = {"jak", "kdy", "kam", "kde", "proč"}
bez_pta, s_pta = set(), set()
for veta in pole.uloziste.nacist_korpus("query"):
    for t in veta:
        if t["form"].lower() in kolidujici and any(
                a.startswith("PronType=Int") for a in t["acts"]):
            bez_pta.add("|".join(sorted(a for a in t["acts"] if not a.startswith("Ptá="))))
            s_pta.add("|".join(sorted(t["acts"])))
print(f"  {', '.join(sorted(kolidujici))}: bez Ptá= {len(bez_pta)} podpis,"
      f" s Ptá= {len(s_pta)}")
ok(len(bez_pta) == 1, "čekal jsem, že tyhle tvary bez Ptá= splývají do jednoho")
ok(len(s_pta) == len(kolidujici), "Ptá= je nerozdělil na samostatné")

print("\n— skládání otázky ze slovníku —")
pole = nove_pole(polomer_dotazu=2)
skladac = Skladac(pole.ziskat_slovnik(), pole.zdroj, pole.skladac, Okno(2, False))
skladac.pridat_slovo("se").pridat_slovo("jmenuje").zvolit_kotvu("kdo")
skladac.pridat_slovo("alfons").prepnout_cil("pes")
print("  offsety:", " ".join(f"{t}({d:+d})" for t, d in skladac.spocitat_offsety()))
slozeno = skladac.slozit_vektor()
print(f"  vektor: {' '.join(slozeno['vektor'][:4])} … "
      f"({len(slozeno['vektor'])} položek)")
print(f"  mimo okno: {slozeno['mimo_okno'] or 'nic'}"
      f" · neznámé: {slozeno['nezname'] or 'nic'}"
      f" · nejisté: {', '.join(slozeno['nejiste']) or 'nic'}")
ok([d for _, d in skladac.spocitat_offsety()] == [-2, -1, 0, 1], "offsety nesedí")
ok(not any(a.startswith("0:") for a in slozeno["vektor"]),
   "střed se dostal do vektoru, ač je nastavený mimo")
ok(not slozeno["nezname"], "některý tvar nemá ve slovníku aktivace")
ok(not slozeno["mimo_okno"], "kotva se hlásí jako mimo okno, ač je jen mimo vektor")
ok(skladac.vzor.je_hotovy(), "úplný vzor se netváří jako hotový")

uzsi = Skladac(pole.ziskat_slovnik(), pole.zdroj, pole.skladac, Okno(1, False))
uzsi.vzor = skladac.vzor
uz = uzsi.slozit_vektor()
print("  při r=1 vypadne:", ", ".join(uz["mimo_okno"]))
ok("se" in uz["mimo_okno"], "r=1 nevyřadilo slovo na offsetu -2")
ok(len(uz["vektor"]) < len(slozeno["vektor"]), "užší okno nedalo kratší vektor")

print("\n— kotva při odebírání slov —")
skladac.odebrat_slovo(0)
print(f"  po odebrání „se\": {' '.join(skladac.vzor.slova)} · kotva {skladac.vzor.kotva}")
ok(skladac.vzor.kotva == 1, f"kotva se neposunula: {skladac.vzor.kotva}")
ok(skladac.vzor.tazaci_tvar() == "kdo", "kotva ukazuje na jiné slovo než kdo")
popis = popsat_zaznam(skladac.vzor.do_slovniku())
print(f"  popis: {popis['typ']} · {popis['text']}")
ok(popis["text"] == "-1:jmenuje 0:kdo +1:alfons",
   "popis s offsety nesedí: " + popis["text"])
skladac.odebrat_slovo(skladac.vzor.kotva)
ok(skladac.vzor.kotva == -1, "odebrání kotvy ji nezrušilo")
stary = popsat_zaznam({"q": ["kdo"], "f": ["psa"]})
ok(stary["typ"] is None and stary["text"] == "kdo",
   "starší záznam bez kotvy se čte špatně")

print("\n— sítko: střed v okně, ale projde z něj jen jmenované —")
# Bez sítka je střed buď celý venku (a zápor, čas i osoba jsou neviditelné,
# protože je v češtině nese slovo samo), nebo celý uvnitř (a šablona přestane
# být obálkou okolí). Sítko je mezi tím.
mimo = nove_pole()
cely = nove_pole(stred_uvnitr=True)
uzke = nove_pole(stred_atributy=("Polarity",))
print(f"  šablon faktů — mimo {mimo.fakta.pocet_sablon()}"
      f" · celý střed {cely.fakta.pocet_sablon()}"
      f" · jen Polarity {uzke.fakta.pocet_sablon()}")
ok(uzke.nastaveni.stred_uvnitr,
   "stred_atributy nezapnulo střed do okna — filtrovalo by se, co v okně není")
ok(uzke.nastaveni.stred_atributy == ("Polarity",),
   f"stred_atributy se uložily jinak: {uzke.nastaveni.stred_atributy}")
ok(Nastaveni(stred_atributy="Polarity, Tense").stred_atributy
   == ("Polarity", "Tense"), "řetězec se nerozdělil po čárkách")


def na_stredu(pole):
    """Aktivace, které se ve vektorech objevily na offsetu 0."""
    return {a.split(":", 1)[1] for info in pole.fakta.vypsat_sablony().values()
            for a in info["vec"] if a.startswith("0:")}


ok(not na_stredu(mimo), "střed nastavený mimo se přesto dostal do vektoru")
ok(len(na_stredu(cely)) > 1, "celý střed do vektoru nepustil skoro nic")
prosaklo = {a for a in na_stredu(uzke)
            if a != "∅" and not a.startswith("Polarity")}
print(f"  na offsetu 0: celý {len(na_stredu(cely))} různých"
      f" · přes sítko {sorted(na_stredu(uzke))}")
ok(not prosaklo, f"sítkem prosáklo, co nemělo: {sorted(prosaklo)}")
ok(mimo.fakta.pocet_sablon() <= uzke.fakta.pocet_sablon()
   <= cely.fakta.pocet_sablon(),
   "sítko nedrží mezi oběma krajnostmi")
# Sousedům sítko nesmí sáhnout — filtruje se podle offsetu, ne plošně.
ok(any(a.startswith("-1:") and "Polarity" not in a
       for info in uzke.fakta.vypsat_sablony().values() for a in info["vec"]),
   "sítko ořezalo i sousední sloty, ne jen střed")

print("\n— stupňované sítko: blízko podrobně, daleko hrubě —")
# Slot navíc stojí sdílení tím víc, čím jemnější je to, co se v něm vidí.
plne = nove_pole(polomer_faktu=2, polomer_dotazu=2)
hrube = Pole(UlozisteSouboru(config=CONFIG),
             sitko=SitkoStupnovane({1: (), None: ("UPOS",)}))
hrube.nastavit_polomery(2, 2).postavit()
print(f"  r=2 plně {plne.fakta.pocet_sablon()} šablon"
      f" · r=2 s UPOS na ±2 {hrube.fakta.pocet_sablon()}")
ok(hrube.fakta.pocet_sablon() < plne.fakta.pocet_sablon(),
   "hrubší pohled do dálky nedal míň šablon")
daleko = {a.split(":", 1)[1] for info in hrube.fakta.vypsat_sablony().values()
          for a in info["vec"] if a.startswith(("-2:", "+2:"))}
ok(all("=" not in a or a == "∅" for a in daleko),
   f"na ±2 prosáklo víc než UPOS: {sorted(a for a in daleko if '=' in a)[:5]}")
blizko = {a for info in hrube.fakta.vypsat_sablony().values()
          for a in info["vec"] if a.startswith(("-1:", "+1:"))}
ok(any("Case=" in a for a in blizko), "±1 přišlo o podrobnost, ač mělo zůstat plné")

# Past, do které jsem spadl: sítko podstrčené jako šev nezapne střed do okna
# a filtruje se pak vzduch. Zkouška to pozná.
ok(filtruje_stred(SitkoStredu(("Polarity",))), "zkouška nepoznala filtrující sítko")
ok(not filtruje_stred(SitkoVse()), "zkouška označila propouštějící sítko za filtrující")
ok(not filtruje_stred(SitkoStupnovane({1: (), None: ("UPOS",)})),
   "sítko, které střed nechává být, se hlásí jako filtrující")
ok(filtruje_stred(SitkoStupnovane({0: ("Polarity",), None: ()})),
   "sítko filtrující nultý offset se nepřiznalo")

print("\n— hrubé vrstvy jsou zadarmo, dokud je sítko nepoužije —")
# Odvozená hodnota je FUNKCÍ jemné, takže vektor sice prodlouží, ale nesmí
# rozdělit ani jednu šablonu. Kdyby rozdělila, není to hrubší vrstva téhož,
# ale nový atribut — a ten by měl stát to, co každý jiný.
katalog = list(UlozisteSouboru(config=CONFIG).nacist_vertikaly())
bez = Pole(UlozisteSouboru(config=CONFIG),
           zdroj=ZdrojZTokenu(katalog, odvozene=()))
bez.nastavit_polomery(2, 2).postavit()
s_vrstvami = nove_pole(polomer_faktu=2, polomer_dotazu=2)
delka = {jm: sum(len(i["vec"]) for i in p.fakta.vypsat_sablony().values())
              // max(1, p.fakta.pocet_sablon())
         for jm, p in (("bez", bez), ("s", s_vrstvami))}
print(f"  bez vrstev {bez.fakta.pocet_sablon()} šablon (délka {delka['bez']})"
      f" · s vrstvami {s_vrstvami.fakta.pocet_sablon()} (délka {delka['s']})")
ok(bez.fakta.pocet_sablon() == s_vrstvami.fakta.pocet_sablon(),
   f"hrubá vrstva rozdělila šablony: {bez.fakta.pocet_sablon()}"
   f" → {s_vrstvami.fakta.pocet_sablon()}")
ok(delka["s"] > delka["bez"], "hrubá vrstva se do vektoru vůbec nedostala")

hrube = {a.split(":", 1)[1] for info in s_vrstvami.fakta.vypsat_sablony().values()
         for a in info["vec"] if ":Trida=" in a or ":Uloha=" in a}
print(f"  v poli: {', '.join(sorted(hrube))}")
ok(hrube, "hrubé vrstvy se v poli neobjevily")
ok(all(v["a"] in {c["a"] for c in s_vrstvami.vypsat_vertikaly()}
       for v in vertikaly_odvozenych()),
   "hrubé sloupce nejsou v katalogu, mřížka by je neuměla zobrazit")

# Teprve sítko, které pustí hrubou vrstvu a jemnou ne, něco změní.
jen_hrube = Pole(UlozisteSouboru(config=CONFIG),
                 sitko=SitkoStupnovane({1: (), None: ("HRUBĚ",)}))
jen_hrube.nastavit_polomery(2, 2).postavit()
print(f"  na ±2 jen hrubě → {jen_hrube.fakta.pocet_sablon()} šablon")
ok(jen_hrube.fakta.pocet_sablon() < s_vrstvami.fakta.pocet_sablon(),
   "hrubý pohled na ±2 nedal míň šablon než plný")
daleko = {a.split(":", 1)[1] for info in jen_hrube.fakta.vypsat_sablony().values()
          for a in info["vec"] if a.startswith(("-2:", "+2:"))}
ok(all(a == "∅" or a.startswith(("Trida=", "Uloha=")) for a in daleko),
   f"na ±2 prosáklo i něco jemného: {sorted(a for a in daleko if '=' in a)[:4]}")

# Prohlížeč musí dostat věty tak, jak je vidí jádro — jinak by měl v katalogu
# sloupec, který v žádném tokenu nenajde.
vyvezeno = korpusy_ven(s_vrstvami)
prvni = next(t for veta in vyvezeno["facts"] for t in veta)
ok(any(a.startswith("Trida=") for a in prvni["acts"]),
   f"vyvezený token nemá hrubou vrstvu: {prvni['acts']}")
ok("form" in prvni and "upos" in prvni, "vývozem se ztratilo, co token nesl")

print("\n— export ven —")
pole = nove_pole()
ven = pole_ven(pole)
ok(set(ven) >= {"nastaveni", "klic_mapovani", "slovnik", "f", "q"},
   "v exportu chybí klíč")
ok(len(ven["f"]["radky"]) == pole.fakta.tok.pocet_radku(), "rozvržení řádků nesedí")
ok(ven["f"]["cisla"]["sablon"] == 71, "čísla v exportu nesedí s modelem")
print(f"  klíčů: {', '.join(sorted(ven))} · řádků f {len(ven['f']['radky'])}")

print("\n— config umí data přesměrovat —")
jinam = Config(data="/tmp/pole2-test-data")
ok(jinam.data == "/tmp/pole2-test-data", "absolutní cesta se přepsala")
ok(jinam.slozka("corpora").endswith("corpora"), "podadresář struktury nesedí")
ok(Config(data="data").data.endswith("/data"), "relativní cesta se nezakotvila")
print(f"  {jinam}")

shutil.rmtree(_DOCASNA, ignore_errors=True)
print(f"\n{chyb} KONTROL SELHALO" if chyb else "\nvšechny kontroly prošly")
sys.exit(1 if chyb else 0)
