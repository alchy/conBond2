# Návrh: systém, který se k odpovědi dopracuje

Zadání na **nový systém** jako syntézu dvou projektů — `conBond` (graf,
role, vztahy) a `conBond2` (aktivační pole, šablony, poctivost). Ne
refaktoring ani portace. Popisuje, co má systém umět a z čeho se má
skládat, aby to uměl.

Píšu to po dni, kdy obojí běželo vedle sebe a nikdy se nepotkalo. To
setkání je celý ten návrh.

---

## 0 · Věta, ze které všechno plyne

> **Rozumět textu znamená umět ho zakódovat tak, aby totéž vypadalo stejně.
> Všechno ostatní — vyhledání, odvození, vyloučení — je pak jedna operace
> nad tím kódem.**

Z toho plynou tři důsledky, které rozhodují o architektuře:

1. **Pravidlo nejde indukovat nad textem, jen nad referenčním jazykem.**
   Teprve kódování způsobí, že se dvě různé věty dají porovnat. Proto se
   `tchán = otec ∘ manžel` vyčetl z faktů sám, kdežto „kdo zemřel dřív,
   nemohl toho druhého znát" muselo být napsáno rukou — čas nebyl
   zakódovaný.
2. **Když se v jádře objeví `if` podle druhu dat, chybí šev.** Není to
   sloh, je to diagnostika. Každý takový `if` je jev, který ještě není
   kódovaný.
3. **Nula je nejnebezpečnější hodnota.** „Data to nemají" a „nepodařilo se
   zeptat" vypadají stejně. Systém musí ty dva stavy rozlišovat na úrovni
   typů, ne komentářů.

---

## 0b · Dvě podmínky, které platí pro každý řádek kódu

### KNIHOVNA, ne aplikace

Jádro je **importovatelná knihovna bez závislostí a bez vstupně-výstupní
vrstvy**. Server, prohlížeč, příkazová řádka i cizí program jsou jen
klienti; žádný z nich není zdroj pravdy.

```
jadro/          čistá knihovna — standardní knihovna jazyka a nic víc
  kodovani/     token → vektor · věta → hrana · entita → jméno
  abstrakce/    šablony · pravidla · arita · graf
  odvozovani/   diagram · rozměry · tabulka · skládání
  jazyk/        profily z JSON

klienti/        server, CLI, REPL, notebook — všechny volají totéž API
data/           korpusy, profily, etalony — nikdy v kódu
```

Praktické důsledky, které se musí dodržet, jinak z toho knihovna není:

* **Žádné globální stavy.** Pole, znalost i rozhovor jsou objekty, které
  se dají vytvořit vedle sebe; dva korpusy v jednom procesu musí jít.
* **Žádné čtení cest z konstant.** Všechno přes `Config`, aby šel test
  ukázat na jinou složku než provoz. (conBond2 na to doplatil: testy
  měřily proti pracovní kopii a tvrdily čísla z jiných dat.)
* **Žádný tisk z jádra.** Log je šev; klient rozhodne, kam jde.
* **Parser je klient, ne závislost.** Jádro dostane hotové tokeny.
  Těžké knihovny (TensorFlow) patří k přípravě dat, ne k běhu.
* **Deterministické API.** Táž data a táž otázka dají tutéž odpověď včetně
  pořadí kandidátů — jinak se nedá měřit.
* **Serializovatelné výsledky.** Každý výstup jde do JSON beze ztráty,
  včetně řetězu doložení.

Zkouška, že se to povedlo: *cizí program si naimportuje jádro, podá si
vlastní tokeny a dostane odpověď i s řetězem — bez serveru, bez souborů,
bez sítě.*

### MULTILANGUAGE, všechno v JSON definicích

**V kódu nesmí být jediné slovo přirozeného jazyka.** Ani v podmínce, ani
v porovnání, ani v konstantě.

```
jazyk/cs.json     tázací tvary · role · spojky · měsíce · prázdná slova
jazyk/en.json     totéž pro angličtinu
jazyk/de.json     …
```

Co všechno musí být v profilu, protože to dnes v kódu je nebo bylo:

| položka | příklad | dnes |
|---|---|---|
| tázací tvar → typ | `kdy → Typ=cas` | ✓ v JSON |
| tázací tvar → role | `komu → komu_cemu` | ✓ v JSON |
| víceslovné tvary | `jako co → jako_co` | ✓ v JSON |
| deprel → role podle pádu | `obl + Dat → komu_cemu` | ✓ v JSON |
| role podle přísudku | `jmenovat: jak → koho_co` | ✓ v JSON |
| prázdná slova | předložky, spony | ✓ v JSON |
| role žádající jméno | `koho_co` chce NOUN | ✓ v JSON |
| předložka → role | `jako → jako_co` | ✓ v JSON |
| vztahová slovesa | `znát, setkat se` | ✓ v JSON |
| **základní vztahy** | `otec, matka, syn…` | ✗ **v kódu** |
| **prázdná slovesa** | `být, mít` | ✗ **v kódu** |
| **jmenné UPOS** | `PROPN` jako jméno osoby | ✗ **v kódu** |
| **pády přísudku** | `Nom, Ins` | ✗ **v kódu** |
| **značky jmen** | `NameType=Giv/Sur/Geo` | ✗ **v kódu** |
| **skládání jména** | příjmení přes `flat` | ✗ **v kódu** |
| **tvar odpovědi** | „upřesni prosím, koho myslíš" | ✗ **v kódu** |

Poslední řádek je podstatný a snadno se zapomene: **texty odpovědí jsou
taky jazyk.** Patří do profilu jako šablony s dosaditelnými místy, ne do
f-stringů v jádře.

Co zůstává univerzální a do profilu **nepatří**: geometrie pole (offsety,
odsazení), slučování stejných vektorů, monotónnost, skládání hran,
pravidla diagramu. To je logika, ne jazyk.

Zkouška, že se to povedlo: *přidání jazyka je nový soubor v `jazyk/` a
model parseru — ani jeden řádek v jádře.* A protikladná zkouška:
*`grep` na česká slova v `jadro/` nevrátí nic.*

Pozor na past, na kterou conBond2 narazil: prohlížeč překládal **data**
(`Trida=pomocny → Class=help`), takže výstup pole musí být označený
`lang` a `translate="no"`. Jazyk profilu je jazyk textu, ne jazyk
uživatelského rozhraní — jsou to dvě různé věci a smí se lišit.

---

## 1 · Dvě dědictví a co si z nich vzít

| | conBond | conBond2 |
|---|---|---|
| **základ** | graf entit a hran | aktivační pole tokenů |
| **abstrakce** | role, vztahy, pravidla | šablona = stejný vektor |
| **silné** | dosah, vzdálené vazby, dialog s tématem | poctivost, měřitelnost, švy |
| **slabé** | šlo vymyslet cestu odkudkoli kamkoli | pytel vět, žádné hrany |
| **co přenést** | graf, role, odvozování, paměť tématu | pole, šablony, monotónnost, etalon |

**Ani jeden neuměl to druhé.** conBond měl hrany, ale ne abstrakci nad
tvarem vět. conBond2 má šablony, ale odpovídá z pytle vět o osobě — a
proto na „Kde byl Jan uvězněn?" odpoví „Praha", protože Praha v tom pytli
náhodou leží.

---

## 2 · Jádro: tři zrna téhož kódu

Systém kóduje text na **třech zrnech** a na všech platí týž zákon:
*stejné se slučuje, rozdílné se rozlišuje, a co se slilo, nese své
doložení.*

```
zrno        jednotka      abstrakce nad ním     co z toho plyne
─────────────────────────────────────────────────────────────────────
TOKEN       slovo         ŠABLONA               druh věty
            + aktivace    (stejný vektor)       „tohle je věta o narození"

VĚTA        tvrzení       HRANA                 fakt
            (kdo, co, čí) (predikát nad jmény)  „narodil(Jirásek, 1851)"

ENTITA      jméno         GRAF                  souvislost
            + doložení    (vážené sousedství)   „Hrabal ↔ Havel přes Koláře"
```

Dnešní conBond2 má první řádek hotový, druhý vyrábí (`edges.py`, 163 hran)
a třetí používá jen na jednu otázku. **Nový systém je má propojit tak, že
odpověď prochází všemi třemi.**

### Zákon skládání

```
šablona  řekne  KTERÉ VĚTY se ptáme        (druh)
hrana    řekne  CO se v nich tvrdí         (obsah)
graf     řekne  KTERÁ z nich patří k otázce (zaměření)
```

Na příkladu, na kterém dnešní systém selhal:

```
Kde byl Jan uvězněn?
  šablona:  věty tvaru „<osoba> byl uvězněn v <místo>"
  hrany:    uvěznit(kdo, kde) — žádná s Janem
  graf:     hrana Jan–Praha u události věznění neexistuje
  ⇒ MLČENÍ, a je to správná odpověď
```

Dnešní systém odpoví „Praha", protože se ptá jen na to, jestli slovo leží
ve stejném dokumentu.

---

## 2b · Identifikace věty: vzor, šablona a MATICE VZTAHŮ mezi nimi

Tohle je jádro odpovídání a dnešní systém to nemá.

```
VZOR       jeden konkrétní vektor    jak vypadá TAHLE věta
ŠABLONA    třída stejných vektorů    druh vět, které vypadají takhle
MATICE     vztahy mezi šablonami     které druhy spolu souvisejí
```

### Proč nestačí šablona sama

Otázka „Kde byl Jan uvězněn?" se přeloží na vzor. Ten se sotva kdy trefí
na šablonu **přesně** — otázka a odpověď mají jiný slovosled, jiný pád,
jinou osobu. Kdyby se hledala jen totožnost, systém by mlčel skoro vždy.

Proto matice: **šablona otázky ukazuje na šablony odpovědí**, a ten vztah
se buduje z dat, ne z pravidel.

```
Š(„Kde byl X uvězněn?")  ─┬─ 0,81 ─→  Š(„X byl uvězněn v <místo>")
                          ├─ 0,62 ─→  Š(„<místo>, kde X seděl")
                          └─ 0,44 ─→  Š(„X strávil ve vězení <čas>")
```

### Jak matice vzniká

Tři nezávislé zdroje, každý s vlastní vahou a **vlastním doložením**:

1. **Sdílené kotvy.** Dvě šablony, jejichž věty opakovaně mluví o týchž
   entitách a týchž hodnotách, spolu souvisejí. Tohle je čistě
   pozorovatelné a nepotřebuje jazykovou znalost.
2. **Společná hrana.** Šablona A vyrábí `uvěznit(kdo, kde)` a šablona B
   taky — pak jsou to dva způsoby, jak říct totéž. Hrana je společný
   jmenovatel různých formulací.
3. **Dialog.** Člověk potvrdí nebo opraví: „ne, tohle je o něčem jiném."
   Nejdražší zdroj, ale nejpřesnější — a musí být vidět, které vazby
   odtud pocházejí.

Matice je **řídká a vážená**, drží se jen nad nějakým prahem, a každá
vazba nese počet dokladů. Bez počtu se nedá poznat vazba z tisíce vět od
vazby z jedné.

### Co tím systém získá

```
dnes:   otázka → slova → věty, kde ta slova leží  (pytel)
nově:   otázka → vzor → šablony → věty toho DRUHU (třída)
```

Rozdíl je vidět přesně na tom selhání: v pytli vět o Nerudovi Praha leží.
Ve třídě vět o **věznění** Neruda není, a odpověď je mlčení.

---

## 2c · Aproximace ze vztahů a učení

Systém se nesmí zastavit na tom, co je doložené. Musí umět **přiblížit se**
— a přiznat, že se přiblížil.

### Tři způsoby aproximace

**1 · Přes šablonu (tvarová aproximace).**
Nejbližší šablona v matici místo přesné shody. „Kde se narodil X?" a
„X pochází z <místo>" nejsou totéž, ale odpověď leží ve stejném poli.
Míra = váha v matici.

**2 · Přes vztah (skládaná aproximace).**
Když chybí přímá hrana, složí se z existujících — `tchán = otec ∘ manžel`.
Míra = délka řetězu a nejslabší článek v něm.

**3 · Přes zařazení (typová aproximace).**
Co platí o třídě, platí obvykle o členu. `liška ⊂ divoké zvíře`, o divokých
zvířatech se ví, kde žijí. Míra = vzdálenost ve svazu a to, jestli existuje
konkrétnější pravidlo, které ji přebíjí.

Všechny tři vracejí **odstupňované tvrzení**, ne holé „ano" — a formulace
se musí lišit slovy, ne jen v detailu.

### Učení: čtyři smyčky

```
1. Z FAKTŮ NA PRAVIDLA
   kde se složená cesta opakovaně kryje s doloženou hranou, je to pravidlo
   doklad / navíc / spor — a `navíc` NENÍ chyba, pole je monotónní

2. Z PRAVIDEL NA FAKTY
   odvozená hrana je vstup dalšího odvozování i dalšího učení
   ⇒ vrstva se zavírá sama na sebe

3. Z DAT NA MÍRY
   arita (kolik hodnot smí entita mít), výlučnost rozměru, váhy v matici
   — všechno MĚŘENO, nikdy zadáno

4. Z DIALOGU NA VŠECHNO
   člověk potvrdí, opraví, doplní — a jeho hrana přebíjí korpus,
   protože kdo systém opravuje, dělá to proto, aby ho opravil
```

Smyčka 2 je ta, kvůli které to celé stojí za to: text říká, že Věra je
manželka Karla a Karel otec Lucie. Že je Věra matka Lucie, neříká
**nikde** — a přesto to plyne, a je to nový fakt, nad kterým se dá učit
dál.

### Co učení nesmí

* **Nepřepisovat doložené.** Naučené pravidlo smí odvozovat, ne měnit to,
  co v textu stojí.
* **Nepřijímat pod prahem.** Pravidlo ze tří dokladů je náhoda. A práh se
  neohýbá po měření.
* **Neztrácet, odkud to je.** Každá naučená hrana nese pravidlo, premisy
  a počet dokladů — jinak ji nejde vzít zpátky, až se ukáže špatná.

---

## 3 · Vrstvy

```
┌─ PŘÍJEM ────────────────────────────────────────────────────────┐
│ text → věty → rozbor → tokeny s aktivacemi                      │
│ jediný klient parseru, zkratky scelené na jednom místě          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─ KÓDOVÁNÍ (referenční jazyk) ───────────────────────────────────┐
│ token   aktivace do vektoru, sítko rozhoduje co projde          │
│ věta    hrany (predikát, kdo, čí, doložení)                     │
│ entita  jméno scelené jedním pravidlem, varianty slité          │
│ rozměr  osy: čas, místo, počet, zařazení — každá jen ZNAČKUJE   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─ ABSTRAKCE ─────────────────────────────────────────────────────┐
│ šablony  slučování stejných vektorů                             │
│ pravidla z definic (kopulová věta) i z faktů (indukce)          │
│ arita    kolik hodnot smí entita mít — MĚŘENO, ne zadáno        │
│ graf     vážené sousedství s doložením u každé hrany            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─ ODVOZOVÁNÍ ────────────────────────────────────────────────────┐
│ diagram  uzly = tvrzení a jejich negace, šipky = implikace      │
│          modus ponens · modus tollens · úplný rozbor            │
│ skládání term = base ∘ via, fixpoint                            │
│ rozměry  vylučují (nikdy nepotvrzují)                           │
│ tabulka  přiřazení s „právě jeden"                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─ ODPOVĚĎ ───────────────────────────────────────────────────────┐
│ druh · obsah · ŘETĚZ DOLOŽENÍ · míra jistoty                    │
└─────────────────────────────────────────────────────────────────┘
```

### Subsystémy: pojmenovaní agenti, každý s jednou prací

Převzato z conBondu, kde se to osvědčilo — pojmenovaná věc se dá vypnout,
změřit a nahradit. Každý subsystém **jen značkuje**; rozhodování je jinde.

```
CHRONOS   čas       datum, rok, událost narození a úmrtí, osa času
TOPOS     místo     kde se to stalo; NameType=Geo proti Giv/Sur
METRON    počet      kolik; a co počet NENÍ (řadové číslovky)
BIO       životopis  definiční závorka: narození, úmrtí, místa
DRUH      zařazení   jmenný přísudek — „kdo/co to je", i se záporem
SPEECH    přímá řeč  kdo co komu řekl; rám uvozovací věty
MNEMOS    paměť      co člověk řekl o sobě a o světě V TOMHLE rozhovoru
HERMES    kanály     kudy odpověď ven — web, terminál, hlas, soubor
ROLES     větné členy 12 rolí z rozboru, tabulkou z profilu
NAMES     jména      scelení, varianty, osoby proti dokumentům
```

Pravidla, která platí pro každý z nich:

* **Jen značkuje.** Chronos řekne „tohle je čas", ne „tohle je odpověď".
* **Dá se vypnout.** A musí být měřitelné, co se tím ztratí.
* **Značka nese zdroj.** Aby šlo poznat, který subsystém se plete.
* **Mlčení je platný výstup.** Agent, který nic nenašel, není chyba.

MNEMOS stojí trochu stranou: nepracuje s korpusem, ale s tím, co člověk
řekl. Jeho hrany mají jinou proveninci a **přebíjejí korpus**, protože
kdo systém opravuje, dělá to proto, aby ho opravil.

### Švy (jediná místa, kde se smí lišit implementace)

Dnešních pět zůstává, tři přibývají:

```
ZdrojAktivaci   odkud se berou atributy tokenu
Uloziste        odkud se čte a kam se píše
SkladacVektoru  jak se z okolí udělá vektor
Slucovac        kdy jsou dva vektory táž šablona
Sitko           co z kterého offsetu projde
─────────────────────────────────────────────
Hranovac    ✚   jak se z věty stane hrana         (dnes natvrdo)
Rozmer      ✚   jak se jev zakóduje na osu        (čas hotov, místo ne)
Jazyk       ✚   tázací tvary, role, spojky        (dnes cs.json)
```

`Jazyk` jako šev znamená, že angličtina je soubor, ne větev v kódu.

---

## 4 · Logické schopnosti

Seřazeno podle toho, co která potřebuje. **Všechny vracejí řetěz
doložení**, ne jen výsledek — bez toho je odvozování jen rychlejší způsob,
jak si vymyslet odpověď.

### 4.1 Přímý zásah
Šablona najde věty téhož druhu, hrana z nich vytáhne tvrzení.
*Potřebuje:* šablony, hrany. *Vrací:* větu.

### 4.2 Skládání vztahů
`tchán = otec ∘ (manžel | manželka)`, fixpoint (`praděd` až po `dědovi`).
Pravidla ze **dvou zdrojů**: definiční věta („Tchán je otec manžela") a
**indukce z faktů** — kde se složená cesta opakovaně kryje s doloženou
hranou, je to pravidlo.
*Potřebuje:* hrany, slučování jmen. *Vrací:* řetěz hran.

Tři čísla, ne jedno skóre:
```
doklad   složená cesta trefila doloženou hranu
navíc    cesta dala hranu, kterou korpus nedokládá   ← NENÍ chyba
spor     cesta si odporuje s doloženou hranou
```
`navíc` není chyba, protože pole je monotónní. Kdyby vstupovalo do
rozhodování, každé pravidlo by nad neúplným korpusem propadlo.

### 4.3 Výroková dedukce (šipkový diagram)
Uzly jsou tvrzení a jejich negace, šipky implikace.
```
modus ponens   p ⇒ q, p platí    ⇒ q platí
modus tollens  p ⇒ q, q neplatí  ⇒ p neplatí
```
Modus tollens je ten podstatný — dopředným čtením se z úlohy vyčte
polovina. Spor se **hlásí, nepřepisuje**.

### 4.4 Úplný rozbor případů
Když není dáno nic a přesto něco plyne. Vyzkoušet všechna ohodnocení je
úplné tam, kde je propagace jen rychlá; cenou je 2^n, takže strop a
poctivé „neumím" místo hodinového počítání.

### 4.5 Vylučování rozměrem
```
čas       intervaly se nepřekrývají  ⇒ NE     překrývají se  ⇒ nic
místo     v týž čas jinde            ⇒ NE     totéž místo    ⇒ nic
počet     tři ≠ dvacet               ⇒ NE     shoda          ⇒ nic
zařazení  ryba a savec se vylučují   ⇒ NE     obojí zvíře    ⇒ nic
```
**Rozměr umí vyvracet, ne potvrzovat.** Pravá strana je vždycky prázdná.
A rozměr sám netvrdí, která značka znamená „nemožné" — jen dvojici
označí, a **rozhodne měření** nad doloženými dvojicemi. Jinak je to
zapečený axiom o patro níž.

### 4.6 Výlučnost atributu (arita)
Kolik hodnot smí entita mít, se **měří z dat**: nemá-li v korpusu nikdo
dva otce, je otcovství jednohodnotové. Tvrzení si tím nese vlastní okolí —
z `otec(Karel, Petr)` plyne `¬otec(kdokoli jiný, Petr)`, aniž to kdo psal.

Jedinečnost sedí na **druhém konci hrany**: jedno dítě má jednu matku,
jedna matka může mít dětí kolik chce.

### 4.7 Přiřazovací úlohy
„Právě jeden" je součin, a takový uzel diagram nemá. Vlastní struktura:
tabulka osob × kategorií s omezeními `je / není / spolu / nikdy`. Vrací
**všechna** řešení — úloha se dvěma vypadá při vracení prvního jako
vyřešená.

### 4.8 Odstupňované tvrzení (nové)
Dnešní systém odpovídá {ano, ne, nevím}. To je poctivé, ale je to podlaha.
Přibývá **`podepřeno`**: víc nezávislých cest, spočítaných, s řetězem.

```
doložené    věta to říká                     TVRZENÍ
odvozené    pravidlo to složí, s řetězem     TVRZENÍ
podepřené   n nezávislých cest               PREFERENCE, ne tvrzení
vyloučené   rozměr to vylučuje               TVRZENÍ
nevím       nic z toho                       PŘIZNÁNÍ
```

Podmínka, bez které to sklouzne do hádání: **podepřená odpověď se musí
lišit slovy**, ne jen v detailu, a musí jít rozbalit na svůj řetěz.

### 4.9 Abdukce (nové)
„Co by to vysvětlovalo?" — z `q` a `p ⇒ q` navrhnout `p`. Je to neplatný
úsudek a musí být **označený jako hypotéza**. Cena je v tom, že navrhne,
co ověřit — ne v tom, že odpoví.

### 4.10 Defeasibilita a specifičnost (nové)
„Ptáci létají; tučňák ne." Obecné pravidlo platí, dokud ho nepřebije
konkrétnější. Specifičnost = **hloubka ve svazu podtříd**, výjimky =
záporné hrany (`Typ=druh_ne`). Obojí už v datech je.

Tohle je ta schopnost, která chybí na úlohy typu „Kde bys našel lišku?" —
`liška ⊂ divoké zvíře ⇒ obvykle žije v přirozeném prostředí`, a „kurník"
je výjimka, ne protipříklad.

---

## 5 · Co to má umět (zkoušky, ne přání)

Každá položka je zkouška, kterou lze spustit, a u každé stojí, co k ní
chybí dnes.

```
✓ hotovo dnes   ◐ částečně   ✗ chybí
```

**Fakt z jedné věty**
```
✓ Kdy se narodil Alois Jirásek?     23. srpna 1851 Hronov
✓ Jako co pracoval Alois Jirásek?   učitel
✓ S kým se přátelil Bohumil Hrabal? s Jiřím Kolářem
```

**Poctivé mlčení**
```
✓ Kdy se narodil Sherlock Holmes?   o něm korpus nic neví
✓ S kým se oženil Bohumil Hrabal?   mlčí — text o tom nemluví
✗ Kde byl Jan uvězněn?              dnes „Praha“; má mlčet
```

**Zápor jako fakt**
```
✓ Kdo je Božena Němcová?            NE „realistkou“ (věta říká, že není)
◐ Proč není realistkou?             důvod je v téže větě, role `proc`
```

**Doptání**
```
✓ Kdo je Novák?                     upřesni: Arne · Bohumil · Ivo
✓ Kdo je Čapek?                     upřesni: Josef · Karel
✗ Kdo byl Jan?                      dnes Neruda; má nabídnout i Křtitele
```

**Vztah a vzdálenost**
```
✓ Mohl Karel Čapek znát Boženu Němcovou?   ne — životy se nepřekrývají
✓ Znal se Hrabal s Havlem?                 nevím, ale vede cesta …
✗ Kdo je bratr Karla Čapka?                hrana existuje, nepoužívá se
```

**Odvozený fakt**
```
✓ (na vztahovém textu) děd, strýc, teta — věty, které nikde nestojí
✗ Kdo je Petrův tchán?                    v dialogu nezapojeno
```

**Výroková úloha**
```
✓ věštkyně, vnuk, večírek     (Bartlová, kap. 4.4)
✓ milovníci umění             (přiřazovací tabulka)
✗ zadání z volného textu      dnes se úloha zadává ručně
```

**Učení dialogem**
```
✓ „Božena Němcová je spisovatelka.“ → přijato, přebije korpus
◐ „Tchán je otec manžela.“          → pravidlo z definice, mimo dialog
✗ „Ne, Jan byl uvězněn v Machaeru.“ → oprava faktu za běhu
```

**Návaznost**
```
✓ Kdo je Ježíš? → Syn Boží;  Čí? → z Boha
   (předchozí odpověď se stane aktivací — elipsa bez zvláštního mechanismu)
```

---

## 5b · Dialog s člověkem

Systém není vyhledávač s okénkem. Rozhovor je **rovnocenný zdroj pravdy**
vedle korpusu a musí umět všechno, co člověk v rozhovoru běžně dělá.

### Co má rozumět

```
OTÁZKA NA OBSAH      Kde se narodil Hrabal?          → pole
OTÁZKA NA VZTAH      Je Krakatit dílo?               → znalost
OTÁZKA NA SOUVISLOST Mohl Čapek znát Němcovou?       → graf + rozměr
TVRZENÍ              Krakatit je román.              → nová hrana
OPRAVA               Ne, Jan byl uvězněn v Machaeru. → přebije korpus
DEFINICE             Tchán je otec manžela.          → nové pravidlo
OSOBNÍ FAKT          Mám rád knedlíky.               → mnemos
VZKAZ                Vyřiď Jindrovi, že přijdu.      → schránka
NAVÁZÁNÍ             Čí?  ·  A kdy?  ·  A on?        → elipsa z tématu
METAOTÁZKA           Odkud to víš?  ·  Co víš o X?   → řetěz doložení
SPOLEČENSKÉ          Dobrý den. · Děkuju.            → odpověď, ne rozbor
```

### Zapamatování faktu od uživatele (MNEMOS)

Co člověk řekne o sobě nebo o světě, se **uloží a nese jinou proveninci
než korpus**. Tři vlastnosti, které to musí mít:

1. **Přebíjí korpus.** Kdo systém opravuje, dělá to proto, aby ho opravil.
   Ale to staré se nemaže — jen ustoupí, a v detailu je vidět obojí.
2. **Ví, čí to je.** Fakt patří tomu, kdo ho řekl. Bez identity se
   „mám rád knedlíky" nedá k nikomu vztáhnout, a systém se má radši
   zeptat, než hádat.
3. **Je odvolatelné.** „Zapomeň, co jsem říkal o X" musí jít — a musí
   zmizet i to, co se z toho odvodilo.

Naučené hrany vstupují do **téhož** odvozování jako korpusové: pravidla
z faktů, arita i diagram na ně platí stejně. To je celý smysl jednoho
referenčního jazyka.

### Vyřizování vzkazů

Vzkaz je fakt s **adresátem a časem doručení**. Systém ho přijme, potvrdí
a doručí, až se adresát ozve.

```
uloz:    „Vyřiď Jindrovi, že přijdu v pátek."
         → vzkaz(od=já, komu=jindra, co=…, kdy=…)
doruc:   Jindra se přihlásí → „Máš vzkaz od Honzy: …"
```

Zásada, která to drží při zemi: **vzkaz se nedoručuje odhadem.** Když
není jisté, kdo je „Jindra", systém se doptá — stejně jako u jmen
v korpusu. Špatně doručený vzkaz je horší než nedoručený.

### Metaotázky jsou plnohodnotné

„Odkud to víš?" musí umět odpovědět vždycky, protože každá odpověď nese
řetěz. To není luxus — je to jediná obrana proti tomu, aby se odvozené
vydávalo za doložené.

```
Kde se narodil Hrabal?  →  Židenice
Odkud to víš?           →  věta 14 dokumentu bohumil_hrabal, agent Bio,
                           definiční závorka, `Udal=narozeni`
```

### Elipsa bez zvláštního mechanismu

Navazující otázka nemá vlastní mechanismus — **předchozí odpověď se stane
aktivací** a zúží pole jako každý jiný signál. Ověřeno: „Kdo je Ježíš?" →
„Syn Boží"; „Čí?" pak svítí slovy `syn` a `boží` a pole klesne z 557 vět
na 34.

Podmínka: doplňuje se **jen** u otázky, která sama nic nenese. Jinak by si
předchozí odpověď táhla do všech dalších otázek.

---

## 6 · Nedotknutelné zásady

Tohle není styl. Každá zásada je zapsaná po chybě, která bez ní vznikla.

1. **Monotónnost.** Chybějící hrana znamená „nikdo se neptal", ne „neplatí".
   Kladné tvrzení z nepřítomnosti neplyne nikdy; záporné z **doložené**
   neslučitelnosti ano.
2. **Každý závěr nese svůj řetěz.** Kandidát nese větu, odvozený fakt nese
   pravidlo a premisy, vyloučení nese osu a hodnoty.
3. **Odvozené se nesmí splést s doloženým.** Ani v datech, ani ve
   formulaci odpovědi.
4. **Mlčení je odpověď.** Stroj, který si vymyslí, je horší než stroj,
   který mlčí. Etalon má doménu, kde je správná odpověď mlčení.
5. **Spor se hlásí, nepřepisuje.** Vybrat jednu z odporujících si hodnot a
   jet dál je tichá chyba — nejhorší druh.
6. **Nejslabší důkaz potřebuje nejsilnější pole.** Role smí mluvit jen
   tam, kde agent není a kde je čím zúžit.
7. **Práh se neohýbá po měření.** Když vyjde 16 dokladů proti prahu 20,
   pravidlo se nepřijme — jinak se měřítko přizpůsobuje výsledku.
8. **Dvoustupňové měření.** *Dosah* (je odpověď mezi kandidáty) a *zúžení*
   (je první). Samotný dosah nic neznamená — vrátit všechno dá 100 %.

---

## 7 · Čeho se vyvarovat

Zapsáno z chyb, které se během jednoho dne staly víckrát.

**Neměřit šablonu jako ranker.** Byla vyzkoušena jako řadič kandidátů,
vyšla hůř, a bylo to uzavřeno jako „nefunguje". Špatná otázka: šablona má
kandidáty **matchnout**, ne mezi nimi vybírat.

**Neladit váhy, když chybí struktura.** Půlhodina ladění skóre entit,
remíz a rozšíření skončila třemi vrácenými opravami — a dvě z nich si
vzájemně vypnuly účinek.

**Nespoléhat na jeden signál napříč jeho platností.** `Ent=` je jméno
dokumentu; u životopisu je to i osoba, u biblické knihy ne. Bez toho řezu
vzniklo `poslat(bible 1 korintským, timoteo)`.

**Místa propojí všechno.** Praha stojí v tisících vět, takže přes ni vede
cesta od každého ke každému a vypadá to jako nález. Rozbor přitom místo od
člověka odlišuje sám.

**Měřit dřív než stavět.** Vrstva postavená a měřená až potom skončila
přiznáním, že ukázka byla vydávána za výsledek.

---

## 7b · Vizualizace: viewBase jako ZÁKAZNÍK, ne součást

Systém musí být vidět. Ne logem, ale obrazem toho, čím právě myslí.

`viewBase` (Canvas, TerminalWindow) se připojuje **přes veřejné API jako
kdokoli jiný** — o vnitřnostech neví nic. Kdyby sahala do dat přímo,
nešla by vypnout, a přesně to se na stroji bez displeje dělá.

Čtyři pohledy, převzaté z conBondu, kde se osvědčily:

```
/view doc    DOKUMENTY korpusu a jejich blízkosti
             po tahu se rozsvítí ten, ze kterého odpověď přišla
             stabilní mapa — mění se pomalu

/view word   ROZSVÍCENÁ SLOVA pole a jejich vodivosti
             uzly vznikají a hasnou s každým tahem
             ⇒ je vidět, čím stroj právě myslí, ne jen kde to našel

/view vzor   ŠABLONY a matice vztahů mezi nimi        (nové)
             která šablona ukazuje na kterou a jak silně

/view graf   ENTITY a hrany s doložením               (nové)
             cesta, po které odpověď přišla, zvýrazněná
```

Plus dvě okna: **DIALOG** s promptem a **AKTIVACE** bez promptu (režim,
počet kandidátů, zdroj, řetěz).

Zásada: **vizualizace se bez stroje vědomě nespustí.** Prázdné okno je
horší než jasná hláška.

---

## 7c · Dokumentace jako součást, ne příloha

Platí pravidlo, na kterém stojí čitelnost obou projektů:

> **Každá metoda má vysvětlení alespoň principiální, a u každého řezu
> stojí, po jaké naměřené chybě vznikl.**

Konkrétně:

* **Docstring vysvětluje PROČ, ne co.** Co dělá kód, je vidět z kódu.
* **U každé konstanty a prahu stojí, odkud se vzal.** „Šestnáct místo
  sedmi" bez důvodu je magické číslo; s důvodem je to záznam měření.
* **Chyba se zapisuje do kódu, ne jen do commitu.** Řez, který vznikl
  proto, že systém odpověděl „ve svých prózách" na otázku po rodišti, to
  musí mít napsané u sebe — jinak ho někdo za půl roku „zjednoduší".
* **Příručka s diagramy volání** pro každý průchod (příjem, stavba,
  dotaz, dialog, učení).
* **Spustitelné ukázky** vedle textu: `scripts/diagram.py` ukáže krok za
  krokem, co se v odvozování děje. Ukázka, kterou lze spustit, nezastará.

---

## 8 · Měření

Nový systém musí mít od prvního dne to, co má conBond2:

```
test/core.py            jádro, bez sítě a bez korpusu
scripts/etalon.py       kurátorované otázky psané rukou + scénáře
scripts/etalon_*.py     cizí sady, ať se nemeasuruje jen na svém
scripts/diagram.py      logické úlohy se známým řešením
```

**Kurátorovaná sada je nenahraditelná.** Generované otázky mají odpověď
z konstrukce a nikdy neřeknou, jestli systém pozná, že neví.

**Vícetahové scénáře.** Některé vlastnosti se jednou otázkou změřit
nedají — že naučené přebije korpus, je vidět až tehdy, když se systém
nejdřív něco naučí.

**Brána se měří taky.** Otázka, která neprojde do pole, nemá odpověď, i
kdyby ji pole mělo. Stalo se to při každém přidání nové cesty.

**Testuje se každý směr, ne jen ten šťastný.** Ke každé schopnosti patří
čtveřice zkoušek, a chybí-li kterákoli, není ta schopnost hotová:

```
1. UMÍ            správný vstup → správná odpověď
2. MLČÍ           chybějící data → přiznání, ne výmysl
3. DOPTÁ SE       nejednoznačný vstup → otázka zpět, ne volba
4. OHLÁSÍ SPOR    odporující si vstup → hlášení, ne tichý výběr
```

Dnešní etalon má domény přesně kvůli tomu — `zápory` měří mlčení a bez ní
by se vylepšování dosahu odměňovalo i tehdy, když roste konfabulace.

Výchozí stav k porovnání: **40 otázek, 85 % dosah, 65 % první, scénáře 2/2.**

---

## 9 · Co vědomě neděláme

- **Šíření aktivace po hranách.** conBond ho měl; pole se tím ROZŠIŘUJE a
  my ho potřebujeme zúžit. Z paměti tématu se přebírá jen `reinforce`
  a `decay`.
- **Pravděpodobnostní skóre bez řetězu.** Číslo, které nejde rozbalit na
  doložení, je hádání s desetinnou čárkou.
- **Doplňování chybějících faktů ze světa.** Systém smí odvozovat jen
  z toho, co má — z korpusu, z dialogu, z pravidel. Když neví, řekne to.
- **Jeden benchmark jako cíl.** CommonsenseQA je konstruovaná proti
  vyhledávání v grafu (distraktory pocházejí z téhož okolí téhož pojmu),
  takže měří hlavně to, co nám chybí. Užitečná jako zátěž, ne jako meta.

---

## 10 · Pořadí stavby

Podle závislostí, ne podle atraktivnosti.

### Krok nula: SCAFFOLD dřív než cokoli jiného

Nejdřív se navrhne a postaví **kostra**: adresáře, švy jako abstraktní
třídy, prázdné profily, `Config`, log, testovací běh, a **jedna zkouška,
která projde skrz naprázdno** — text dovnitř, prázdná odpověď ven, ale
celou cestou.

Teprve do hotové kostry se vkládají vrstvy. Důvod je praktický: v obou
předchozích projektech vznikly nejhorší vazby tam, kde se vrstva přidávala
do něčeho, co pro ni nemělo místo — odtud „odpovídač nesahá na šablony".

### Data se přebírají z obou projektů

Nic se nesbírá znovu. K dispozici je:

```
z conBond2   korpus 26 051 vět s rozborem, agenty a koreferencí
             etalon 40 kurátorovaných otázek + scénáře
             jazykový profil cs.json
             vertikály (300 sloupců pole)
z conBond    etalon 95 otázek (tři režimy včetně `clarify`)
             dialogové scénáře
             slovník synonym (1016 skupin)
             tabulka vztahů jako odvozovací pravidla
             graf entit s vahami podle větného členu
```

Licence: Wikipedie **CC BY-SA 4.0**, ekumenický překlad Bible je
**autorský a do veřejného repozitáře nesmí** (jen Kralická). Zdroje se
vedou v `ZDROJ.md` a přenášejí se s daty.

```
0. kostra knihovny + jazykový profil   ← všechno ostatní se o ně opře
1. příjem + kódování tokenů        (conBond2 to má, přenést beze změny)
2. HRANY z vět                     ← všechno ostatní na nich stojí
3. jména: scelení, varianty, osoby vs dokumenty
4. šablony do odpovídací cesty     ← tohle je ta chybějící spojka
5. graf zaměřený na hranu, ne na spoluvýskyt
6. diagram jako společný tvar odpovědi
7. rozměry: čas hotov, místo a počet dopsat
8. pravidla z definic i z faktů, arita
9. odstupňovaná tvrzení a abdukce
10. defeasibilita a specifičnost
```

Kroky 2–4 rozhodují o tom, jestli systém odpoví „Praha", nebo mlčí. Zbytek
je nadstavba, která bez nich stojí na písku.
