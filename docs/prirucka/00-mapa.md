# Mapa — co kudy teče

Příručka je psaná pro vývojáře, který o projektu neví nic. Ke každému
mechanismu je **princip** (nezávisle na kódu), **kontrakt** (co bere, co
vrací, co mění na disku) a **ukázka** ze skutečného korpusu.

**Značky důvěry.** *Ověřeno* = výstup jsem spustil a je v textu opsaný.
*Převzato* = popis sedí se zdrojovým kódem, ale sám jsem to nespouštěl.

| díl | co řeší |
|---|---|
| [01 · Extrakce](01-extrakce.md) | syrový text → korpus vět |
| [02 · Pole](02-pole.md) | korpus → vektory → šablony |
| [03 · Dotazování](03-dotazovani.md) | otázka → aktivace → kandidáti |
| [04 · Tvorba otázek](04-otazky.md) | korpus → zlatá sada, měření |
| [05 · Zaměření tématu](05-tema.md) | výřez, domény, přehled vzorů |
| [06 · Dialog a znalost](06-dialog.md) | věta → tvrzení → odvození |
| [07 · Rejstřík metod](07-metody.md) | každá metoda a její role |

---

## Stav, ke kterému se čísla vztahují

*Ověřeno, 31. 7. 2026*

```
korpus     25 755 vět · 479 859 tokenů · 86 dokumentů
pole       440 142 řádků · 388 632 středů · 162 391 šablon · poměr 0.418
slovník    56 985 tvarů · 298 vertikál
```

---

## Pět workflow

Šipka `→` je volání, odsazení je vnoření. Jména jsou skutečné metody.

### A · Extrakční — z textu se stane korpus

```
scripts/baseline.py vse
│
├─ krok_vety()                         data/raw/*.txt → _vety.json
│   └─ Cistic.ze_slozky()
│       └─ Cistic.ze_souboru() → z_textu() → vycistit_radek()
│                                             └─ sceli_zkratky()   ← CHOKEPOINT
│
├─ krok_rozbor(config)                 _vety.json → _tokeny.json
│   └─ Rozbor.vety_slovniku()
│       └─ Rozbor.rozebrat() → poslat()      ← jediný klient UDPipe
│                            → z_conllu() → Token.do_slovniku()
│
├─ krok_koreference()                  doplní Ent= a Kor=
│   ├─ hlavni_osoba()                  identita = jméno souboru
│   ├─ podmet_korene() · je_treti_osoba() · je_to_ona()
│   └─ rod_cislo()                     ověření shody
│
└─ krok_zapis()                        _tokeny.json → data/corpora/facts.json
    ├─ oznacit_korpus()                agenti: Bio → Chronos → Metron → Topos
    │   └─ Agent.oznac() → Agent.najdi() → Naveska.do_slovniku()
    ├─ Vypovedi.oznacit()              Vyp=proza / Vyp=seznam
    └─ doplnit_vertikaly()             nové aktivace dostanou sloupec
```

### B · Pole — z korpusu se stanou šablony

```
Pole.postavit()
│
├─ Pole.vypsat_vertikaly()             uložené + hrubé vrstvy
│   └─ bez_odvozenych() + vertikaly_odvozenych()
├─ Pole.pripravit_zdroj()   → ZdrojZTokenu
├─ Pole.pripravit_sitko()   → SitkoStredu
│   └─ filtruje_stred()                hlídač: filtruje se vzduch?
│
├─ Pole.rozprostrit(strana)            pro fakta i dotazy
│   └─ Tok.rozprostrit()
│       ├─ Tok.vybrat_tokeny()         interpunkce podle zrna
│       ├─ Tok.odsadit_vetu()          r prázdných řádků kolem věty
│       └─ Tok.vyrobit_prazdne()
│
├─ Pole.naplnit_slovnik()              SPOLEČNÝ oběma stranám
│   └─ Slovnik.naplnit_z_toku() → zapsat_radek() → zalozit_nebo_najit()
│
└─ Pole.postavit_stranu(strana)        VLASTNÍ každé straně
    └─ Strana.postavit()
        ├─ Tok.vypsat_stredy()
        ├─ Strana.zaradit_stred()
        │   ├─ Okno.urcit_sloty()      i-r … i+r
        │   ├─ Strana.slozit_vektor()
        │   │   ├─ Strana.aktivace_slotu()
        │   │   │   ├─ ZdrojZTokenu.vypsat_aktivace()
        │   │   │   │   ├─ odfiltrovat_typy() · dopocitat_hrube()
        │   │   │   │   └─ seradit_kanonicky()   ← pořadí je významné
        │   │   │   └─ Sitko.propustit(offset)   ← co z toho místa projde
        │   │   └─ SkladacRetezcem.popsat_slot()
        │   ├─ SlucovacShodou.zaradit()          ← tady vzniká ŠABLONA
        │   └─ Strana.pripsat_k_sablone()
        └─ Strana.sestavit_vazby()               slovo ↔ šablona
```

### C · Dotazovací — z otázky se stane odpověď

```
Odpovidac.odpovedet(text)
│
├─ Odpovidac.rozsvitit(text)                    CO SE AKTIVUJE
│   ├─ obsahove_tvary()      → Jazyk.je_prazdne()
│   ├─ najit_entitu()        osoba je AKTIVACE Ent=, ne slovo
│   ├─ jmena_v_otazce() · sedi_cele_jmeno()     řez na cizí jméno
│   ├─ vety_tvaru()          sloveso je TVAR ve slovníku
│   └─ vážení                věta = bod za slovo + bod za entitu
│
├─ Odpovidac.rozsirit()      volitelně: Znalost.potomci()
├─ Jazyk.na_co_se_pta()      Kdy → Typ=cas · Kde → Typ=misto
└─ Odpovidac.sebrat()        úseky toho druhu v poli
```

### D · Tvorba otázek — z korpusu se stane zlatá sada

```
scripts/otazky.py generuj
│
├─ koren_vety() · entita()              bez osoby otázka nemá koho
├─ naveska_typu(veta, typ, koren)
│   ├─ přeskočí Udal=zivot              cizí životní rozpětí
│   └─ visi_na(veta, i, koren)          hranice klauzule, ne počet kroků
├─ zvratne() · doplneni()               „se", neúplná slovesa
└─ zápis: dok + vd                      STABILNÍ klíč, ne pozice
```

### E · Zaměření tématu — na co se právě dívám

```
prohlížeč                     python
─────────────────────────────────────────────────────
výřez vět        →  Vyrez  →  Prevod.radek() · veta()
                              strana_ven() přečísluje indexy
list Vzory       →            prehled_sablon(strana, od, pocet, razeni)
list Dialog      →            Rozhovor.poslat() → Odpovidac
scripts/domeny.py             přenos vzorů mezi doménami
```

---

## Kde co leží

```
core/            knihovna — zdroj pravdy, funguje bez serveru i prohlížeče
  ingest.py        A · příjem textu
  flow.py          B · rozprostření vět
  window.py        B · okno kolem středu
  sources.py       B · zdroj aktivací, skládač, slučovač
  sieve.py         B · sítko — co z kterého offsetu projde
  derived.py       B · hrubé vrstvy nad jemnými
  lexicon.py       B · společný slovník
  side.py          B · jedna strana pole
  field.py         B · fasáda celého průchodu
  answers.py       C · odpovídání
  language.py      C · jazykový profil (česká slova v JSON)
  tvrzeni.py       F · mluvnice tvrzení a znalost
  dialog.py        F · rozhovor
  export.py        E · výřez a převod na JSON
  health.py        —  kontrola zdraví dat
  agents/          A · Bio, Chronos, Metron, Topos

server/          HTTP — tenká vrstva, nic nepočítá
scripts/         nástroje — baseline, otázky, měření, etalon
data/            korpusy, vertikály, mapování, znalost, zlaté sady
```
