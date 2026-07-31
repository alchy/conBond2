# 01 · Extrakce — ze syrového textu korpus

Vstup je složka `.txt` souborů, výstup jeden `data/corpora/facts.json`.
Čtyři kroky, každý se dá spustit sám:

```
python3 scripts/baseline.py vety         text → věty
python3 scripts/baseline.py rozbor       věty → tokeny (UDPipe)
python3 scripts/baseline.py koreference  doplní podměty
python3 scripts/baseline.py zapis        agenti, druh výpovědi, korpus
python3 scripts/baseline.py vse          všechno za sebou
```

---

## 1 · Čištění — `Cistic`

**Princip.** Wikipedie i knihy nesou řádky, které nejsou výpovědi: nadpisy
sekcí, odrážky, tabulky. Jdou pryč hned, protože každý další krok je dražší.
A hned tady se scelí zkratky s tečkami — je to **jediné místo**, kterým
projde korpus i dotaz, takže se nemůžou rozejít.

**Kontrakt.**

| metoda | bere | vrací | mění |
|---|---|---|---|
| `vycistit_radek(radek)` | řádek | očištěný řádek | — |
| `z_textu(text)` | text | seznam řádků | — |
| `ze_souboru(cesta)` | cesta | seznam řádků | — |
| `ze_slozky(slozka)` | cesta | `{dokument: [řádky]}` | — |

**Ukázka.** *Ověřeno*

```python
>>> from core import Cistic
>>> Cistic().z_textu("== Život ==\n\nR.U.R. je hra[1] Karla Čapka.\nkrátké")
['RUR je hra Karla Čapka.']
```

Nadpis pryč, poznámka `[1]` pryč, řádek kratší než čtyři slova pryč,
`R.U.R.` scelené na `RUR`.

> **Proč zrovna tady.** conBond na to má vlastní modul `normalize.py`
> s jedinou tezí: oprava tokenizace patří na jediný chokepoint. My jsme
> měli dva klienty UDPipe a jeden scelení neměl — korpus tedy mohl mít
> `R.U.R.` rozsekané na tři tokeny a otázka scelené. Obojí by dál
> „fungovalo" a jen mluvilo o jiném slově.

---

## 2 · Rozbor — `Rozbor`

**Princip.** Jeden klient UDPipe pro celý projekt. CoNLL-U ven nepouštíme,
ať se s ním nemusí zabývat ani prohlížeč, ani příprava.

**Kontrakt.**

| metoda | bere | vrací |
|---|---|---|
| `poslat(text)` | text | CoNLL-U jako řetězec |
| `z_conllu(vysledek)` | CoNLL-U | `[[Token, …], …]` |
| `rozebrat(text)` | text | `[[Token, …], …]`, po scelení zkratek |
| `vety_slovniku(text)` | text | tytéž věty jako slovníky pro korpus |
| `lemmata(text)` | text | lemmata jako řetězec (pro pojmy z dialogu) |

**Ukázka.** *Ověřeno*

```python
>>> from core import Rozbor, Config
>>> r = Rozbor(Config.nacist().udpipe)
>>> [t["form"] for t in r.vety_slovniku("R.U.R. je hra Karla Čapka.")[0]]
['RUR', 'je', 'hra', 'Karla', 'Čapka', '.']
>>> r.lemmata("románu díla")
'román dílo'
```

**Tvar tokenu.** `id` a `head` v korpusu ZŮSTÁVAJÍ, `lemma` ne.

```python
{"form": "Narodil", "upos": "VERB", "id": 1, "head": 0,
 "acts": ["VERB", "root", "Gender=Masc", "Number=Sing", "Tense=Past", …]}
```

Do vektoru jde jen `acts`. `id`/`head` jsou mimo ně schválně: bez nich
nejde poznat, co na čem závisí (koreference, generátor otázek), ale do
vektoru se dostat nesmějí. `lemma` se zahazuje — do vektoru patří typ,
ne hodnota.

> **Past, na kterou se doplatilo.** `int(c[0])` spadlo na tokenu `²`,
> protože `"²".isdigit()` je `True`, ale `int()` na tom spadne. Článek
> o betonu má `m²` a shodil stavbu celého korpusu. Správný predikát je
> `isdecimal()` a je teď na jednom místě jako `je_cele_cislo()`.

---

## 3 · Koreference — doplnění podmětu

**Princip.** Životopis mluví o jedné osobě a věty jako „Narodil se v Praze."
podmět vůbec nemají. Takový fakt nejde spojit s otázkou „Kde se narodil
Hrabal?", protože o Hrabalovi neříká nic.

Do textu se ale nic nedopisuje — pole má zůstat obrazem textu. Sloveso
dostane **aktivace navíc**:

```
Kor=prodrop     podmět ve větě chybí
Kor=zajmeno     podmět je zájmeno 3. osoby
Kor=jmenovana   podmět je vyjádřený a je to ona
Ent=hrabal      a tohle je ten, o kom se mluví
```

**Kontrakt.**

| funkce | role v procesu |
|---|---|
| `hlavni_osoba(kdo, vety)` | identita = **jméno souboru**, ne lemma z rozboru |
| `je_koren_slovesa(t)` | jen kořen věty, ne libovolné sloveso |
| `podmet_korene(veta, koren)` | podmět KOŘENE — jinak se pro-drop nenajde |
| `je_treti_osoba(t)` | příčestí bez `Person=` je taky 3. osoba |
| `je_to_ona(podmet, osoba)` | vyjádřený podmět, který je ta osoba |
| `rod_cislo(token)` | ověření shody |

**Ukázka.** *Ověřeno*

```
podměty doplněny  kdo=alois_jirásek  osoba=alois_jirásek  zásahů=125  podíl=27 %
koreference hotova  prodrop=3567  zajmeno=234  jmenovana=689
```

**Tři chyby, které to stálo, a proč jsou v kódu popsané:**

1. *Identita byla holé křestní jméno.* První verze brala první `PROPN`
   v podmětu a dostala „karel", „božena". Fakt navěšený na *Karel* patřil
   všem sedmadvaceti Karlům v korpusu. Jméno souboru je jednoznačné.
2. *Filtr `Person=3` zahodil 1188 z 1588 kořenů.* Čeština v minulém čase
   osobu na slovese nenese — „Narodil se" má jen rod a číslo. Tedy přesně
   ty věty, o které v životopise jde.
3. *Podmět se hledal kdekoli ve větě.* Věty na Wikipedii jsou dlouhé
   a skoro každá má vedlejší větu s vlastním podmětem, takže se pro-drop
   našel v 83 z 3478 vět. Rozhoduje závislost na kořeni.

---

## 4 · Agenti — `Bio`, `Chronos`, `Metron`, `Topos`

**Princip.** Agent nevytěžuje fakt, **dodává do pole aktivace**. Je to
implementace švu `ZdrojAktivaci`, druhý zdroj vedle UDPipe.

Podstatné je rozdělení na TYP a HODNOTU:

```
typ      Typ=cas       → do acts → do vektoru → ZOBECŇUJE
hodnota  1914-03-28    → mimo acts → na vazbu → ROZLIŠUJE
```

Kdyby šlo obojí do vektoru, vzniklo by 244 sloupců `Rok=…` a 19 % z nich by
se vyskytlo jednou — takové šablony se nemohou sdílet nikdy. Cena atributu
je pokrytí × mohutnost a tohle je nejhorší možná kombinace.

**Kontrakt.**

| agent | co hledá | co přeskakuje a proč |
|---|---|---|
| `Bio` | biografická závorka → narození a úmrtí | nedefiniční závorky → jen `Udal=zivot` |
| `Chronos` | roky a data | závorky — jsou to data někoho jiného |
| `Metron` | počty a míry | čtyřmístné roky (Chronosova doména), závorky |
| `Topos` | místa z `NameType=Geo` | závorky |

**Ukázka.** *Ověřeno*

```python
>>> from core.agents import oznacit_korpus
>>> oznacit_korpus(vety)
{'bio': 850, 'chronos': 3018, 'metron': 4621, 'topos': 2615}
```

```
Alois Jirásek ( 23. srpna 1851 Hronov – 12. března 1930 Praha ) byl…
                └─ Typ=cas 1851 · Typ=misto Hronov · Udal=narozeni
                                        └─ Typ=cas 1930 · Udal=umrti
```

> **Proč Bio existuje.** Změřeno: 200 vět mělo závorku s rokem a **všech
> 200 nemělo jedinou časovou návěsku**. Chronos závorky přeskakuje a je to
> správně — bez toho řezu věšel roky rodičů protagonistovi. Bio ten řez
> neruší, jen tuhle jednu konstrukci čte záměrně.
>
> **Dvě pasti v Biu.** Ne každá závorka za jménem je životopis: první verze
> dala „narození" datům manželky a létům studia, takže se to teď přizná jen
> u definiční věty (jméno na začátku + spona za závorkou). A ne každá
> pomlčka dělí: `( 1926 Praha - Libeň – 2011 Praha )` udělalo z Libně
> místo úmrtí, dokud dělič nezačal být en-dash s rokem na obou stranách.

---

## 5 · Druh výpovědi — `Vypovedi`

**Princip.** 57 % „vět" nemá slovesný kořen a je to bibliografie —
`Praha : Academia , 1985 .` Nemaže se to (pole má být obraz textu), ale
označí:

```
Vyp=proza    327 271 tokenů
Vyp=seznam   152 588 tokenů
```

Příznak jde na **každý token**, ne jen na kořen: šablona se skládá ze
sousedů, takže kdyby ho nesl jen kořen, sousedi by o tom nevěděli.

**Ukázka.** *Ověřeno* — bez příznaku mělo **6558 šablon (14 %)** v sobě
řádky z prózy i z bibliografie naráz; s ním nula, za cenu 6 bodů sdílení.

---

## 6 · Zápis a původ

`krok_zapis()` zapíše korpus a přidá dvě pole **mimo `acts`**:

```python
t["dok"] = "alois_jirásek"   # z kterého článku
t["vd"]  = 17                # pořadí věty v článku
```

> **Proč mimo `acts`.** Kdyby se původ dostal do vektoru, rozpadly by se
> šablony po autorech — 86 hodnot na každém tokenu je nejhorší možná
> kombinace pokrytí a mohutnosti. Test to hlídá.
>
> **Proč vůbec.** Bez původu se dá na větu odkazovat jen pozicí v korpusu
> a ta přežije do příští přestavby. Zlatá sada na tom spadla ze 100 % na
> 0 % a nic to neohlásilo.

`doplnit_vertikaly()` nakonec dá každé nové aktivaci sloupec — co nemá
vertikálu, není v poli vidět.
