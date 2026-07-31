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
                  pole_ven, prehled_sablon, vertikaly_odvozenych,
                  Odpovidac, Vyrez)
from core.compose import popsat_zaznam  # noqa: E402
from core.dialog import Rozhovor  # noqa: E402
from core.health import zkontrolovat  # noqa: E402
from core.language import Jazyk  # noqa: E402
from core.tvrzeni import Mluvnice, Znalost  # noqa: E402
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
ok(pole.fakta.pocet_sablon() == 71 and pole.dotazy.pocet_sablon() == 166,
   f"počty šablon nesedí: {pole.fakta.pocet_sablon()}/{pole.dotazy.pocet_sablon()}")
ok(len(pole.fakta.vazby) == 74 and len(pole.dotazy.vazby) == 210,
   "počty vazeb nesedí")
for k, predpona in (("f", "f"), ("q", "q")):
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
# Okno(2, False) = střed MIMO; tenhle test zkoumá právě to, takže se
# nesmí opírat o výchozí nastavení, které má střed v okně.
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
mimo = nove_pole(stred_atributy=(), stred_uvnitr=False)
cely = nove_pole(stred_uvnitr=True, stred_atributy=())
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

print("\n— rozhovor: věta dovnitř, záznam ven —")
# Bez UDPipe se pojmy jen zmenší na malá písmena; na tvary, které mluvnice
# rozlišuje, to stačí a test tím nezávisí na běžícím rozboru.
r = Rozhovor(Znalost())
ok(r.poslat("Krakatit je román.").druh == "tvrzeni", "instance neprošla")
ok(r.poslat("román je druh díla").druh == "tvrzeni", "podtřída neprošla")
z = r.poslat("Krakatit není báseň")
# Druh ZÁZNAMU je „tvrzeni" (přijalo se), druh HRANY je „zapor" (co to je).
ok(z.druh == "tvrzeni" and z.hrana["druh"] == "zapor",
   f"zápor se zapsal jako {z.druh}/{z.hrana and z.hrana['druh']}")
print("  " + " · ".join(f"{z.text} → {z.hrana['druh']}" for z in r.historie))

# Expanze: odpověď nesmí být z přímé hrany, ale přes dva skoky.
ok(r.odpovedet(" Krakatit díla").odpoved.startswith("ano"),
   "expanze nedosáhla přes dvě hrany")
ok(r.odpovedet(" Krakatit film").odpoved.startswith("nevím"),
   "o čem nepadlo slovo, se má říct nevím, ne ne")
r.poslat("Krakatit není báseň")
ok(r.odpovedet(" Krakatit báseň").odpoved.startswith("ne,"),
   "zapsaný zápor se neprojevil v odpovědi")
print(f"  ano/nevím/ne: {r.odpovedet(' Krakatit díla').odpoved}"
      f" | {r.odpovedet(' Krakatit film').odpoved[:5]}"
      f" | {r.odpovedet(' Krakatit báseň').odpoved}")

# Nejasnost drží rozhovor: nedořešená hrana se nesmí ztratit.
z = r.poslat("pes je savec")
ok(z.druh == "nejasnost", f"„pes je savec“ mělo být nejasné, je {z.druh}")
ok(r.ceka_na_rozhodnuti(), "rozhovor po nejasnosti nečeká")
ok(r.poslat("kočka je šelma").druh == "nejasnost",
   "čekající rozhovor přijal další větu a rozdělaná hrana by se ztratila")
ok(r.rozhodnout("podtrida").druh == "tvrzeni", "rozhodnutí neprošlo")
ok(not r.ceka_na_rozhodnuti(), "rozhovor čeká i po rozhodnutí")
print(f"  nejasnost → rozhodnuto → {r.historie[-1].odpoved}")

# A tohle je to učení: nevím → jedna věta → ano.
ok(r.odpovedet(" Alík savec").odpoved.startswith("nevím"), "o Alíkovi se nemá vědět nic")
r.poslat("Alík je pes")
ok(r.odpovedet(" Alík savec").odpoved.startswith("ano"),
   "po přidání věty se odpověď nezměnila — nic se nenaučilo")

# OTÁZKA SE NESMÍ ZAPSAT JAKO TVRZENÍ. „Co je Šmoula?" má tvar „X je Y“ a
# dřív se z tázacího slova stal pojem: přijato „co ∈ šmoula“.
r2 = Rozhovor(Znalost())
r2.poslat("Šmoula je skřítek.")
pred = len(r2.znalost.tvrzeni)
for otazka in ("Co je Šmoula?", "co je Šmoula?", "Kdo je Šmoula?",
               "Je Šmoula skřítek?", "Šmoula je skřítek?", "Je Šmoula drak?"):
    z = r2.poslat(otazka)
    ok(z.druh in ("otazka", "rodokmen"),
       f"„{otazka}“ se zpracovalo jako {z.druh}, ne jako dotaz")
ok(len(r2.znalost.tvrzeni) == pred,
   f"otázky přidaly {len(r2.znalost.tvrzeni) - pred} tvrzení — nesmí přidat žádné")
ok(not any(t.levy in ("co", "kdo") for t in r2.znalost.tvrzeni),
   "tázací slovo se stalo pojmem")
print("  otázky: " + " · ".join(f"{z.text}→{z.druh}" for z in r2.historie[1:4]))

# Věta začínající značkou dřív shodila dělení: hledalo se v odsazeném
# řetězci, dělilo v neodsazeném, a ValueError šel ven jako pětistovka.
for kraj in ("je Šmoula skřítek", "není Šmoula drak", "je", "?"):
    r2.poslat(kraj)          # nesmí spadnout
print(f"  krajní tvary prošly, tvrzení pořád {len(r2.znalost.tvrzeni)}")

# Víceslovný pojem: „Je Šmoula pohádková bytost?" nejde rozdělit podle
# posledního slova — kde je řez, ví až znalost.
r3 = Rozhovor(Znalost())
r3.poslat("Šmoula je skřítek.")
r3.poslat("skřítek je pohádková bytost")
r3.rozhodnout("podtrida")
ok(r3.poslat("Je Šmoula pohádková bytost?").odpoved.startswith("ano"),
   "řez u víceslovného pojmu se nenašel")
print(f"  víceslovný pojem: {r3.historie[-1].odpoved}")

stav = r.vypsat_stav()
ok(set(stav) == {"historie", "znalost", "nalez", "tema", "ceka"},
   f"stav pro prohlížeč má jiné klíče: {sorted(stav)}")
ok(stav["znalost"]["cisla"]["tvrzeni"] == len(r.znalost.tvrzeni), "čísla nesedí")
r.zapomenout()
ok(not r.znalost.tvrzeni and not r.znalost.nadrazene and not r.znalost.zapory,
   "po zapomenutí zůstaly hrany — smazat seznam tvrzení nestačí")

print("\n— jazykový profil: česká slova v JSON, ne v podmínkách —")
j = Jazyk.nacist()
print(f"  {j.kod} ({j.jmeno}) · značek podtřídy {len(j.znacky_podtridy)}"
      f" · tázacích {len(j.tazaci)} · měsíců {len(j.mesice)}")
ok(j.kod == "cs" and j.mesice, "profil se nenačetl")
ok(all(isinstance(x, tuple) for x in
       (j.spona, j.tazaci, j.znacky_podtridy, j.predlozky)),
   "seznamy z JSON nedorazily jako n-tice")
# Vysvětlivky pro člověka (klíče od podtržítka) se nesmí stát daty.
ok(not any(p.startswith("_") for p in Jazyk.__dataclass_fields__),
   "vysvětlivka z JSON se propašovala mezi pole profilu")

# A tohle je ten skutečný zisk: značka přidaná v JSON funguje bez sahání
# do Pythonu. „spadá pod" v kódu nikde není.
m = Mluvnice()
ok("spadá pod" in j.znacky_podtridy, "„spadá pod“ v profilu chybí")
t = m.rozeber("kniha spadá pod dílo")
ok(getattr(t, "druh", None) == "podtrida",
   f"značka z profilu se neuplatnila: {t}")
print(f"  značka jen z JSON: „kniha spadá pod dílo“ → {t}")

# Profil se dá podstrčit; pravidlo o velkém písmenu je příznak, ne slovník,
# protože v němčině by bylo k ničemu — velká jsou tam všechna substantiva.
bez_velkych = Mluvnice(jazyk=Jazyk.ze_slovniku(
    {**{p: list(getattr(j, p)) if isinstance(getattr(j, p), tuple)
        else getattr(j, p) for p in Jazyk.__dataclass_fields__},
     "velke_pismeno_je_instance": False}))
ok(type(bez_velkych.rozeber("Krakatit je román")).__name__ == "Nejasnost",
   "vypnuté pravidlo o velkém písmenu se neprojevilo")
print("  s vypnutým pravidlem o velkém písmenu se „Krakatit je román“ ptá")

print("\n— export ven —")
pole = nove_pole()
ven = pole_ven(pole)
ok(set(ven) >= {"nastaveni", "klic_mapovani", "slovnik", "f", "q"},
   "v exportu chybí klíč")
ok(len(ven["f"]["radky"]) == pole.fakta.tok.pocet_radku(), "rozvržení řádků nesedí")
ok(ven["f"]["cisla"]["sablon"] == pole.fakta.pocet_sablon(),
   "čísla v exportu nesedí s modelem")
print(f"  klíčů: {', '.join(sorted(ven))} · řádků f {len(ven['f']['radky'])}")

print("\n— odpovídač: osoba jako aktivace, sloveso jako tvar —")
# Osoba se podle TVARU najít nedá: čeština podmět zahazuje a identita sedí
# jako aktivace Ent=. Hledání podle tvaru dalo na spisovatelském korpusu 1 %.
pole = nove_pole()
odp = Odpovidac(pole)
ok(odp.je_na_obsah("Kde se narodil Karel?"), "otázka na obsah se nepoznala")
ok(not odp.je_na_obsah("Je Krakatit dílo?"), "otázka na vztah se čte jako obsah")
ok(not odp.je_na_obsah("Karel je spisovatel."), "tvrzení se čte jako otázka")
v = odp.odpovedet("Kde se jmenuje Karel?")
ok(set(v) >= {"aktivace", "typ", "kandidati", "odpoved"}, "nález má jiné klíče")
ok(isinstance(v["aktivace"]["vety"], list), "věty jdou ven jako množina, to není JSON")
ok(v["typ"] == "Typ=misto", f"tázací tvar dal {v['typ']}")
print(f"  aktivace: {v['aktivace']['svitici']} · typ {v['typ']}")

print("\n— hlídač zdraví chytí, co dnes proklouzlo —")
# Tři vady za den a ani jedna se neohlásila: nenačtené styly, nespuštění
# agenti, zlatá sada na pozicích vět. Všechny mají týž tvar — A se změnilo,
# B o tom neví.
import json as _json
_d = tempfile.mkdtemp(prefix="pole2-zdravi-")
os.makedirs(os.path.join(_d, "corpora"))
_cfg = Config(data=_d, koren=_d)
_json.dump([[{"form": "a", "upos": "NOUN", "acts": ["NOUN"]}]],
           open(os.path.join(_d, "corpora", "facts.json"), "w"))
_co = {n.co for n in zkontrolovat(_cfg)}
print("  " + " · ".join(sorted(_co)))
ok(any("návěsku agentů" in c for c in _co), "nespuštění agenti se neohlásili")
open(os.path.join(_d, "pole2.html"), "w").write('<link href="css/neni.css">')
ok(any("neexistující soubor" in n.co for n in zkontrolovat(_cfg)),
   "odkaz na chybějící soubor se neohlásil")
shutil.rmtree(_d, ignore_errors=True)

print("\n— původ věty se drží MIMO acts —")
# Bez původu se dá na větu odkazovat jen pozicí v korpusu a ta přežije do
# příští přestavby. Do vektoru ale nesmí: 34 hodnot na každém tokenu by
# rozpadlo šablony po autorech.
korpus = UlozisteSouboru(config=CONFIG).nacist_korpus("facts")
ma_puvod = sum(1 for v in korpus if v and "dok" in v[0])
prosaklo = [a for v in korpus for t in v for a in t["acts"]
            if a.startswith(("Dok=", "Vd="))]
print(f"  vět s původem: {ma_puvod}/{len(korpus)} · v acts prosáklo: {len(prosaklo)}")
ok(not prosaklo, "původ věty se dostal do aktivací a rozpadl by šablony po autorech")

print("\n— téma drží řetěz, ale nezachrání cizí jméno —")
# Bez tématu odpověděla otázka bez jména („Kde se narodil?") pokaždé týmž
# místem — polem složeným ze samotného slovesa. Měřeno: Hrabal i Čapek
# dostali Hronov, protože alois_jirásek je první abecedně.
from core.dialog import Rozhovor as _R  # noqa: E402
from core.tvrzeni import Znalost as _Z  # noqa: E402
_pole = nove_pole()
_o = Odpovidac(_pole)
_r = _R(_Z(), odpovidac=_o)
_r.zahrat("karel")
ok(_r.horka_temata() == ["karel"], "téma se nezahřálo")
# Zmínka je PŘEPNUTÍ tématu, ne hlas: bez tohohle šel dlouho probíraný
# Hrabal přebít Čapka a „Kde se narodil?" odpovědělo Židenice.
for _ in range(5):
    _r.zahrat("karel")
_r.zahrat("alfons")
ok(_r.horka_temata()[0] == "alfons",
   f"pětkrát zmíněné téma přebilo nové: {_r.tema}")
for _ in range(5):
    _r.zahrat(None)
ok(not _r.horka_temata(), f"téma nevychladlo: {_r.tema}")

# Otázka SE JMÉNEM téma nebere — jinak by cizí jméno zachránilo předchozí
# osobu a z paměti tématu by se stala cesta ke konfabulaci.
# Výchozí sada je malá a entity v ní nejsou, tak si jednu podstrčíme —
# zkouší se PRAVIDLO výběru tématu, ne obsah korpusu.
_o.podle_entity["zkouska"] = {0, 1}
_a = _o.rozsvitit("Kdy se narodil Sherlock Holmes?", tema=["zkouska"])
ok(not _a["z_tematu"], "otázka se jménem si vzala téma")
ok(_a["cizi_jmeno"], "cizí jméno se nepoznalo")
_b = _o.rozsvitit("Kde se narodil?", tema=["zkouska"])
ok(_b["z_tematu"] and _b["entita"] == "zkouska",
   f"otázka bez jména téma nevzala: {_b['entita']!r}")
# Téma, které v korpusu není, se nesmí použít — jinak by pole bylo prázdné
# a odpověď by se hledala v ničem.
_c = _o.rozsvitit("Kde se narodil?", tema=["nikdo_takovy"])
ok(not _c["z_tematu"], "vzalo se téma, které v korpusu není")
print(f"  téma se bere jen bez jména · chladne na {len(_r.tema)} po pěti tazích")

print("\n— cizí jméno znamená nevím, ne odpověď o někom jiném —")
# Bez tohohle řezu odpověděl systém na „Kdy se narodil Sherlock Holmes?"
# datem někoho jiného: entita nesedla, pole se složilo ze samotného slovesa
# a to svítí u půlky korpusu. Vymyšlená odpověď je horší než mlčení.
odp = Odpovidac(nove_pole())
for otazka in ("Kdy se narodil Sherlock Holmes?", "Kde zemřel Napoleon Bonaparte?"):
    v = odp.odpovedet(otazka)
    ok(v["aktivace"]["cizi_jmeno"], f"„{otazka}“ se netváří jako cizí jméno")
    ok(not v["kandidati"], f"na „{otazka}“ systém odpověděl: {v['odpoved']!r}")
# Shoda na JEDNOM kuse jména nestačí — „Marie Curie" trefila Marii Majerovou.
ok(not odp.sedi_cele_jmeno(["Marie", "Curie"], "marie_majerová"),
   "půlka jména prošla jako celá shoda")
ok(odp.sedi_cele_jmeno(["Karel"], "karel_čapek"), "úplná shoda neprošla")
print("  mlčí na neznámá jména a nespoléhá na půlku jména")

print("\n— výřez: ven jde kousek, čísla zůstávají celá —")
# Pole se staví CELÉ. Kdyby se stavělo z výřezu, přestaly by být šablony
# šablonami korpusu a sdílení by se počítalo z náhodného vzorku — přesně ten
# omyl, kvůli kterému dřív vyšel poměr 0.95.
pole = nove_pole()
cely = pole_ven(pole, s_korpusy=True)
kus = pole_ven(pole, s_korpusy=True, vyrezy={"f": Vyrez(1, 3), "q": Vyrez(0, 5)})
cf, kf = cely["f"]["cisla"], kus["f"]["cisla"]
print(f"  celý: {cf['vet']} vět, {cf['radku']} řádků, {len(cely['f']['sablony'])} šablon"
      f" · výřez: {kf['vyrez']['vet']} vět, {kf['vyrez']['radku']} řádků,"
      f" {len(kus['f']['sablony'])} šablon")
ok(kf["vet"] == cf["vet"] and kf["radku"] == cf["radku"] and kf["sablon"] == cf["sablon"],
   "výřez přepočítal globální čísla — pak by korpus vypadal malý")
ok(kf["vyrez"]["vet"] == 3, f"výřez má {kf['vyrez']['vet']} vět, čekány 3")
ok(len(kus["f"]["radky"]) == kf["vyrez"]["radku"], "poslaných řádků je jiný počet, než hlásí")
ok(len(kus["f"]["sablony"]) < len(cely["f"]["sablony"]), "výřez neubral šablony")
ok(len(kus["korpusy"]["facts"]) == 3, "korpus se neořízl na výřez")

# Indexy se PŘEČÍSLUJÍ, aby prohlížeč pracoval s hustými poli. Nic nesmí
# ukazovat mimo poslané řádky — jinak by se hrany kreslily vedle.
n = len(kus["f"]["radky"])
ok(all(0 <= i < n for s in kus["f"]["sablony"].values() for i in s["radky"]),
   "šablona ukazuje na řádek mimo výřez")
ok(all(0 <= i < n for v in kus["f"]["vazby"] for i in v["vyskyty"]),
   "vazba ukazuje na řádek mimo výřez")
ok(all(0 <= int(i) < n for i in kus["f"]["sloty"]), "slot je u řádku mimo výřez")
ok(all(0 <= r[0] < 3 for r in kus["f"]["radky"]), "číslo věty se nepřečíslovalo")
# Slot mířící ven z výřezu je null, ne cizí řádek.
mimo = [d for sl in kus["f"]["sloty"].values() for j, d in sl if j is None]
print(f"  slotů mířících ven z výřezu: {len(mimo)} (posílají se jako null)")

# Velikost vzoru se výřezem nemění — to je ta podstatná informace.
spolecna = set(cely["f"]["sablony"]) & set(kus["f"]["sablony"])
ok(all(kus["f"]["sablony"][t]["celkem_tvaru"]
       == len(cely["f"]["sablony"][t]["tvary"]) for t in spolecna),
   "výřez zmenšil hlášenou velikost vzoru")

prehled = prehled_sablon(pole.fakta, od=0, pocet=5)
ok(prehled["celkem"] == cf["sablon"], "přehled vzorů nepočítá všechny šablony")
ok(len(prehled["sablony"]) == 5, "přehled nevrátil požadovaný počet")
ok(all("radky" not in s for s in prehled["sablony"]),
   "přehled vzorů posílá řádky, ač je nepotřebuje")
serazeno = [s["tvaru"] for s in prehled["sablony"]]
ok(serazeno == sorted(serazeno, reverse=True), f"vzory nejsou od největšího: {serazeno}")
print(f"  přehled: {prehled['celkem']} vzorů, největší sdílí {serazeno[0]} tvarů")

print("\n— role: větný člen z rozboru, ale jen tam, kde agent není —")
from core.roles import Role  # noqa: E402

_role = Role(Jazyk.nacist())

# Tabulka, ne kód: pád rozhoduje dřív než výchozí hodnota, jinak by
# „řekl Janovi“ bylo určení místa.
def _tok(upos, dep, *rysy, lemma="x", form="x", tid=1, head=0):
    return {"form": form, "lemma": lemma, "upos": upos,
            "acts": [upos, dep] + list(rysy), "id": tid, "head": head}

ok(_role.role_tokenu(_tok("NOUN", "obl", "Case=Dat")) == "komu_cemu",
   "dativ u obl není komu_cemu")
ok(_role.role_tokenu(_tok("NOUN", "obl", "Case=Loc")) == "kde",
   "lokál u obl není kde")

# Instrumentál sám o sobě není „s kým" — bez předložky se role nepřiřadí,
# jinak by „byl nositelem“ odpovídalo na otázku po společníkovi.
_bez = _tok("NOUN", "obl", "Case=Ins", tid=2, head=1)
ok(_role.role_tokenu(_bez, [_bez]) == "", "holý instrumentál se vydává za s_kym_cim")
_s = _tok("ADP", "case", lemma="s", tid=3, head=2)
ok(_role.role_tokenu(_bez, [_bez, _s]) == "s_kym_cim", "s předložkou role nevznikla")

# Dvě síta nad rolí: prázdné slovo neodpovídá nikdy, jmenná role žádá jméno.
ok(not _role.nese_obsah(_tok("PRON", "obl", "Case=Dat")), "zájmeno prošlo jako odpověď")
ok(not _role.nese_obsah(_tok("VERB", "ccomp", "Case=Acc"), "koho_co"),
   "sloveso prošlo do jmenné role")
ok(_role.nese_obsah(_tok("NOUN", "obl", "Case=Acc"), "koho_co"), "jméno neprošlo")

# Delší tázací tvar bije kratší, jinak „jako CO“ spadne pod „co“.
_j = Jazyk.nacist()
ok(_j.na_co_se_pta("Jako co pracoval Jirásek?") is None,
   "„jako co“ se pořád čte jako Typ=druh")
ok(_role.role_otazky("Jako co pracoval Jirásek?") == "jako_co",
   "„jako co“ nedostalo roli doplňku")
ok(_j.na_co_se_pta("Co napsal Jirásek?") == "Typ=druh",
   "obyčejné „co“ přestalo ukazovat na druh")

print("  pád i předložka rozhodují · prázdná slova a slovesa neodpovídají"
      " · delší tázací tvar vyhrává")

print("\n— vztahy: definiční věta je pravidlo, fakt není —")
from core.relations import fixpoint, odvodit_hrany, pravidla_z_vety  # noqa: E402


def _v(form, upos, dep, *rysy, tid=1, head=0, lem=None):
    return {"form": form, "lemma": (lem or form).lower(), "upos": upos,
            "acts": [upos, dep] + list(rysy), "id": tid, "head": head}


_def = [_v("Tchán", "NOUN", "nsubj", "Case=Nom", tid=1, head=3, lem="tchán"),
        _v("je", "AUX", "cop", tid=2, head=3),
        _v("otec", "NOUN", "root", "Case=Nom", tid=3, head=0, lem="otec"),
        _v("manžela", "NOUN", "nmod", "Case=Gen", tid=4, head=3, lem="manžel"),
        _v("manželky", "NOUN", "conj", "Case=Gen", tid=6, head=4, lem="manželka")]
ok(pravidla_z_vety(_def) == [("tchán", "otec", ["manžel", "manželka"])],
   "definiční věta nedala pravidlo")

# „Karel je otec Petra" je FAKT o Karlovi, ne definice slova. Kdyby PROPN
# procházel, stal by se z každého životopisu zdroj definic.
_fakt = [_v("Karel", "PROPN", "nsubj", "Case=Nom", tid=1, head=3),
         _v("je", "AUX", "cop", tid=2, head=3),
         _v("otec", "NOUN", "root", "Case=Nom", tid=3, head=0, lem="otec"),
         _v("Petra", "PROPN", "nmod", "Case=Gen", tid=4, head=3)]
ok(pravidla_z_vety(_fakt) == [], "vlastní jméno prošlo jako definice")

# Bez spony věta nedefinuje, jen vypráví.
ok(pravidla_z_vety([t for t in _def if "cop" not in t["acts"]]) == [],
   "věta bez spony prošla jako definice")

# Fixpoint: „praděd je otec děda" nedává smysl, dokud není přijat „děd".
_pr = fixpoint([("praděd", "otec", ["děd"], "d"),
                ("děd", "otec", ["matka", "otec"], "d"),
                ("tchán", "otec", ["manžel", "manželka"], "d")],
               {"otec", "matka", "manžel", "manželka"})
ok(set(_pr) == {"praděd", "děd", "tchán"}, f"fixpoint nepřijal vše: {sorted(_pr)}")
ok(all(r["rozsah"] == "jazyk" for v in _pr.values() for r in v),
   "pravidlo nad základními vztahy nemá být vázané na dokument")

_nove = odvodit_hrany([("otec", "karel", "petr"), ("manžel", "petr", "jana"),
                       ("otec", "josef", "karel")], _pr)
_sada = {(h["predikat"], h["kdo"], h["ci"]) for h in _nove}
ok(("tchán", "karel", "jana") in _sada, f"tchán se neodvodil: {_sada}")
ok(("děd", "josef", "petr") in _sada, f"děd se neodvodil: {_sada}")
print(f"  pravidel {len(_pr)} · odvozených hran {len(_nove)}")

print("\n— config umí data přesměrovat —")
jinam = Config(data="/tmp/pole2-test-data")
ok(jinam.data == "/tmp/pole2-test-data", "absolutní cesta se přepsala")
ok(jinam.slozka("corpora").endswith("corpora"), "podadresář struktury nesedí")
ok(Config(data="data").data.endswith("/data"), "relativní cesta se nezakotvila")
print(f"  {jinam}")

shutil.rmtree(_DOCASNA, ignore_errors=True)
print(f"\n{chyb} KONTROL SELHALO" if chyb else "\nvšechny kontroly prošly")
sys.exit(1 if chyb else 0)
