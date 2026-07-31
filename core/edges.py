"""Hrany z korpusu — vrstva osob pod vrstvou dokumentů.

PROČ TO CHYBĚLO. `relations.py`, `graph.py` i diagram hrany PŘEDPOKLÁDAJÍ;
nikdo je nevyráběl a všechny zkoušky si je psaly ručně. Bez téhle vrstvy
je odvozování vyřešená sbírka hlavolamů, ne schopnost nad texty.

Ukázalo se to i jinde: doptání „Kdo je Novák?" mlčelo, ačkoli v korpusu
jsou Novákové čtyři. Entita totiž znamená DOKUMENT (`bohumil_hrabal`,
`rodina_novákovi`), a lidé zmínění uvnitř článků žádné entity nejsou. Tahle
vrstva je vyrábí.

    dokument   o čem je článek        49 životopisů, zvířata, věci
    osoba      kdo je ve větě         tisíce jmen

DVĚ KONSTRUKCE, obě deterministické z rozboru:

    spona      Karel Novák je otec Petra.        otec(Karel Novák, Petr)
               │              │   │    └ nmod Gen  → čí
               │              │   └ root NOUN      → predikát
               │              └ cop
               └ nsubj PROPN                       → kdo

    sloveso    Myslbek znal Nerudu.              znát(Myslbek, Neruda)
               │       │     └ obj                 → čí
               │       └ root VERB                 → predikát
               └ nsubj PROPN                       → kdo

JMÉNO JE CELÉ, NEBO ŽÁDNÉ. `nsubj` ukazuje na „Karel" a „Novák" na něm visí
přes `flat`; bez scelení by hrana patřila všem Karlům. Tatáž past, na kterou
doplatil odpovídač u „Marie Curie" → `marie_majerová`.

PREDIKÁT JE LEMMA, ARGUMENT JE TVAR. Predikátů má být málo, aby se daly
skládat a počítat — proto lemma. Jména se scelují na malá písmena, ale
neohýbají: „Nerudu" a „Neruda" jsou týž člověk a bez lemmatu by to nešlo
poznat. Proto je lemma v korpusu (mimo `acts`, aby se nedostalo do vektoru).

PODMĚT SMÍ DODAT KOREFERENCE. Životopis mluví o jedné osobě a věty jako
„Oženil se s Marií Podhajskou." podmět vůbec nemají (pro-drop). Takových je
v korpusu 15 173 a u 4 111 z nich už koreference doplnila `Ent=` — vrstva
existuje, jen ji nikdo nepoužíval. Bez ní vypadne většina životopisných
hran, tedy právě ty, o které jde.

Hrana odtud je ale SLABŠÍ DŮKAZ: podmět nikdo nenapsal, dopočítala ho
heuristika ze shody rodu a čísla. Nese proto značku `kor`, aby se odvození
opřené o dohad dalo odlišit od odvození opřeného o jméno v textu.

A JEN TAM, KDE JE DOKUMENT OSOBA. `Ent=` je jméno ČLÁNKU, ne člověka.
U životopisu je to totéž, jinde ne — bez tohohle řezu vzniklo:

    oženit(arnošt lustig, věra weislitzová)   správně
    poslat(bible 1 korintským, timoteo)       nesmysl, dokument je kniha
    přibližovat(antarktida, amerika)          nesmysl, dokument je světadíl

Kdo je osoba, se nevypisuje, ale ČTE z dat: má-li dokument doložený rok
narození (agent Bio), je to člověk. Článek o Antarktidě se nenarodil.

CO SE NEBERE. Věta s otazníkem se ptá, neodpovídá — tentýž řez, jaký dělá
agent Druh. A hrana bez dvou jmen není hrana: „Byl prozaik" nespojuje nic,
i když je to pravda.

KAŽDÁ HRANA NESE SVOU VĚTU. Bez toho nemá diagram co vrátit v etapě návratu
do kontextu a odvozený závěr se nedá dohledat.
"""

from typing import Iterable, Mapping, Optional, Sequence

from .roles import deprel, pad

# Slovesa, která nespojují dvě osoby, i když mají podmět i předmět.
# `mít` a `být` jsou příliš obecná: „měl dva syny" je vztah, ale „měl
# úspěch" ne, a rozlišit to bez významu nejde.
PRAZDNA_SLOVESA = ("být", "mít", "moci", "muset", "chtít", "stát")


def jmeno(veta: Sequence[Mapping], token: Mapping) -> str:
    """Celé jméno tokenu — s tím, co na něm visí přes `flat`.

    Vrací prázdno u všeho, co není vlastní jméno. Obecné jméno by z hran
    udělalo tezaurus: „otec(bratr, syn)" nespojuje nikoho."""
    if token.get("upos") != "PROPN":
        return ""
    kusy = [(token.get("id") or 0, (token.get("lemma") or token["form"]).lower())]
    for x in veta:
        if x.get("head") == token.get("id") and deprel(x) == "flat":
            kusy.append((x.get("id") or 0, (x.get("lemma") or x["form"]).lower()))
    return " ".join(t for _, t in sorted(kusy))


def _deti(veta: Sequence[Mapping], token: Mapping, deprely) -> list:
    return [x for x in veta if x.get("head") == token.get("id")
            and deprel(x) in deprely]


def entita_korene(token: Mapping) -> str:
    """Osoba doplněná koreferencí — `Ent=alois_jirásek` → „alois jirásek"."""
    for a in token["acts"]:
        if a.startswith("Ent="):
            return a.split("=", 1)[1].replace("_", " ")
    return ""


def hrany_vety(veta: Sequence[Mapping], cislo: int,
               osoby: Optional[set] = None) -> list:
    """Hrany jedné věty jako [(predikát, kdo, čí, věta)]."""
    if any(t["form"] == "?" for t in veta):
        return []
    out = []
    for t in veta:
        d = deprel(t)
        if d != "root":
            continue
        podmety = _deti(veta, t, ("nsubj", "nsubj:pass"))
        kdo = jmeno(veta, podmety[0]) if podmety else ""
        z_koreference = False
        if not kdo and osoby and not any(
                x.get("upos") == "PROPN" for x in podmety):
            kandidat = entita_korene(t)
            if kandidat in osoby:
                kdo, z_koreference = kandidat, True
        if not kdo:
            continue
        upos = t.get("upos")
        if upos == "NOUN" and _deti(veta, t, ("cop",)):
            # Jmenný přísudek: „Karel je otec Petra." Predikát je ten
            # přísudek, druhý konec visí na něm v genitivu.
            predikat = (t.get("lemma") or t["form"]).lower()
            druzi = [x for x in _deti(veta, t, ("nmod", "nmod:poss"))
                     if pad(x) == "Gen"]
        elif upos == "VERB":
            predikat = (t.get("lemma") or t["form"]).lower()
            if predikat in PRAZDNA_SLOVESA:
                continue
            druzi = _deti(veta, t, ("obj", "iobj", "obl:arg"))
        else:
            continue
        for x in druzi:
            ci = jmeno(veta, x)
            if ci and ci != kdo:
                out.append((predikat, kdo, ci, cislo,
                            "kor" if z_koreference else "text"))
    return out


def osoby_korpusu(vety: Iterable) -> set:
    """Dokumenty, které jsou lidé — poznají se podle doloženého narození.

    Seznam by to být nesměl: korpus roste a ručně udržovaný výčet by tiše
    zastaral. Tohle se přepočítá s každou stavbou."""
    out = set()
    for veta in vety:
        for t in veta:
            if any(a.startswith("Udal=") for a in t["acts"]):
                dok = t.get("dok")
                if dok:
                    out.add(dok.replace("_", " "))
    return out


def hrany_z_korpusu(vety: Iterable, osoby: Optional[set] = None) -> list:
    """Hrany celého korpusu. `osoby` omezuje, u koho smí podmět dodat
    koreference; None znamená spočítat je z týchž dat."""
    vety = list(vety)
    osoby = osoby_korpusu(vety) if osoby is None else osoby
    out = []
    for i, veta in enumerate(vety):
        out.extend(hrany_vety(veta, i, osoby=osoby))
    return out


def prehled(hrany: Sequence) -> dict:
    """Kolik čeho — kvůli posouzení, jestli je na čem stavět."""
    podle: dict = {}
    osoby = set()
    zdroj: dict = {}
    for p, k, c, _, z in hrany:
        podle[p] = podle.get(p, 0) + 1
        zdroj[z] = zdroj.get(z, 0) + 1
        osoby.update((k, c))
    return {"hran": len(hrany), "predikatu": len(podle), "osob": len(osoby),
            "zdroj": zdroj,
            "nejcastejsi": sorted(podle.items(), key=lambda x: -x[1])[:15]}


# ---- slučování variant jména ------------------------------------------

def sjednotit_jmena(hrany: Sequence) -> tuple:
    """Kratší jméno pod delší, když je to JEDNOZNAČNÉ.

    Text střídá „Petr Novák" a „Petr" a pro skládání jsou to dva různí
    lidé — `otec(karel novák, petr)` a `syn(tomáš novák, petr novák)` se
    nepotkají, ačkoli mluví o témž člověku.

    Pravidlo je totéž, jaké měl conBond (`name_subsequence`): jméno, jehož
    všechna slova jsou podmnožinou delšího, je jeho zkrácením.

    REMÍZA SE NESLUČUJE. Kdyby v korpusu byl Karel Novák i Karel Čapek,
    „Karel" nepatří ani jednomu a vybrat delšího znamená hádat. Je to táž
    zásada jako u doptání v dialogu: shoda na půlce jména nestačí.

    Vrací (nové hrany, mapa zkratek) — mapa proto, aby šlo ukázat, co se
    s čím slilo; tiché přejmenování by se špatně hledalo.
    """
    jmena = {k for _, k, _, _, _ in hrany} | {c for _, _, c, _, _ in hrany}
    mapa = {}
    for kratke in jmena:
        slova = set(kratke.split())
        delsi = [j for j in jmena
                 if j != kratke and slova < set(j.split())]
        if len(delsi) == 1:
            mapa[kratke] = delsi[0]
    # Řetěz zkratek: „petr" → „petr novák" → „petr jan novák".
    for k in list(mapa):
        videno = {k}
        while mapa.get(mapa[k]) and mapa[k] not in videno:
            videno.add(mapa[k])
            mapa[k] = mapa[mapa[k]]
    nove = [(p, mapa.get(k, k), mapa.get(c, c), v, z)
            for p, k, c, v, z in hrany]
    return nove, mapa
