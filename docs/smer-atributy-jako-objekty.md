# Atributy jako objekty — revidovaný návrh

Revize návrhu na rozšíření metadat. Souhlasím se směrem, obracím pořadí a
doplňuju měření, které ten návrh na několika místech vyvrací.

## Souhlas se základním posunem

Nestavíme retrieval systém, ale **reprezentaci jazyka**. Aktivační pole má
být jazykový objekt, který půjde použít pro vyhledávání, odvozování i učení.
Z toho plyne, že se má hledět na bohatost reprezentace, ne na to, čím
nahradit embeddingy.

Souhlasím i s diagnózou vrstev — a naše čísla ji potvrzují:

| vrstva | pokrytí tokenů | stav |
|---|---:|---|
| morfologie (UPOS, DEPREL, FEATS) | 100 / 100 / 80 % | velmi dobrá |
| sémantika (`Typ=`, 6 hodnot) | 27 % | velmi slabá |
| diskurz | 0 % | žádná |
| pragmatika | 0 % | žádná |

## Měření, které mění závěr

Návrh říká „máte asi 30 % potřebných metadat" a přidává dvacet kategorií.
Než jsme začali cokoli přidávat, změřili jsme, jak si stojí to, co máme.

Zlatá sada: **54 dvojic otázka → slovo v textu** (z původních 60; šest otázek
na nic neukazuje, protože text odpověď neobsahuje).

Měříme dvě čísla, a **teprve obě dohromady dávají smysl**:

* **strop** — kdyby každá šablona dotazu ukazovala na svůj nejčastější
  faktový cíl, kolik dvojic by sedělo. Měří, jak dobře jde sada *zapamatovat*.
* **křížově** — vynech jednu dvojici, postav mapování ze zbylých 53 a zkus
  na vynechanou otázku odpovědět. Měří, jestli se něco *zobecňuje*.

| r_q | r_f | šablon dotazů | strop | křížově |
|---:|---:|---:|---:|---:|
| 0 | 0 | 23 | 56 % | 13 % |
| 1 | 1 | 19 | 48 % | 19 % |
| **1** | **0** | **19** | **50 %** | **22 %** |
| 2 | 2 | 39 | 74 % | 4 % |
| 3 | 3 | 53 | 98 % | 0 % |
| 8 | 8 | 53 | 98 % | 0 % |

**Strop roste na 98 %, zobecnění padá na nulu.** Při `r=3` je 53 šablon na 54
dvojic — každá otázka má vlastní vzor, takže vynechané otázce nemá co
odpovědět. Vzniká vyhledávací tabulka, ne model.

Nejlepší, co dnes umíme, je **22 %** při nejhrubším nastavení, jaké jsme
zkoušeli. Souběžně platí to, co víme z pole: od `r=2` má každé slovo faktů
vlastní šablonu, poměr šablon ke slovům je 1,00.

### Co z toho plyne pro návrh

Návrh chce **přidávat**. Naše data říkají, že jemnost reprezentace je právě
to, co zobecnění zabíjí. Přidat tři sta booleovských sloupců při stávajícím
pravidle shody posune pole do režimu `r=3`, kde je zobecnění nulové.

Ten návrh opravu obsahuje — váhy, hierarchie, podobnost místo přesné shody —
ale má ji jako body 18 až 20 z dvaceti. **To pořadí je obrácené.** Nové
vrstvy mají smysl teprve tehdy, až se přestane porovnávat na přesnou shodu;
jinak každá další vrstva výsledek zhorší a bude to vypadat, že jsou ty vrstvy
špatné.

> **Výhrada k jistotě těch čísel.** 54 dvojic je málo. Rozdíl mezi 19 % a
> 22 % je šum a nikdo by z něj neměl nic vyvozovat. Rozdíl mezi 98 % stropu a
> 0 % zobecnění šum není — na to je příliš velký a má zřejmou příčinu.

### Oprava: ta metrika měří dvě věci najednou a jednu z nich trestá

Křížová metrika výše předpokládá, že šablona dotazu má mít **jeden** správný
faktový cíl, a když jich má víc, počítá to jako chybu. To je špatně.

Šablona nemá identifikovat konkrétní odpověď, ale **pole odpovědi** — druh
místa, kde odpověď leží. „Kde se narodil X?" má trefit rodiště u všech autorů
naráz; že jich zasáhne dvanáct, je správné chování, ne rozostření. Teprve
druhý krok, zúžení podle entity, z toho pole vybere jednu.

Metrika tedy musí být dvoustupňová:

1. **zásah pole** — obsahuje množina faktových šablon, na které vzor dotazu
   ukazuje, tu správnou? Tohle měří, co dělá aktivační pole.
2. **výběr v poli** — vybere se v něm správná instance podle entity? Tohle
   pole nedělá a dělat nemá; je to úloha pro identitu a koreferenci.

Čísla výše míchají obojí dohromady a odečítají body za to, co je záměr. Než
se z nich bude cokoli vyvozovat, musí se rozdělit — a hlavně přeměřit na
korpusu, kde vůbec je co zasáhnout. Na osmi větách o Karlovi a Alfonsovi
nemá „pole odpovědi" jak vzniknout, protože každý fakt je v textu jednou.

### Doplněno později: na větším korpusu to vypadá jinak

Všechna čísla výše jsou z korpusu o **86 tokenech faktů**. Postavili jsme
baseline z dvanácti wikipedických článků o českých spisovatelích —
**3478 vět, 65 564 tokenů**, tedy zhruba sedmisetnásobek — a přeměřili:

| r | středů | šablon | poměr | vzorů sdílených ≥ 2 slovy |
|---:|---:|---:|---:|---:|
| 0 | 52 150 | 2 514 | **0,05** | 1 261 |
| 1 | 52 150 | 26 205 | **0,50** | 5 586 |
| 2 | 52 150 | 46 197 | 0,89 | 1 440 |
| 3 | 52 150 | 48 940 | 0,94 | 518 |

Na osmi větách vycházel poměr při r=1 na 0,95. Tady vychází **0,50** a
**5 586 vzorů sdílí víc než jedno slovo**. Nejčastější vzor se opakuje
363krát napříč 38 různými slovy.

**Závěr „zobecnění umírá" byl z velké části artefakt velikosti korpusu.**
Na 86 tokenech je každý kontext jedinečný prostě proto, že se text nemá kde
opakovat — nešlo tam nic naměřit, jen se to tvářilo jako měření.

Co platí dál: poměr **pořád roste s r** (0,05 → 0,94), takže směr té úvahy
sedí — jemnější reprezentace znamená míň sdílení. Změnila se ale absolutní
úroveň i to, kde je zlom. Než se cokoli začne přidávat nebo ubírat, patří
to přeměřit tady, ne na osmi větách.

**Sémantické role nad pádem.** `Case=Dat` je tvar, `Recipient` je význam. Pád
se mění s konstrukcí, role ne. Nejsilnější jednotlivý bod celého návrhu.

**Škrtnout morfologické rysy, které nic nenesou:** `NameType` (devět hodnot!),
`Style`, `Hyph`, `Foreign`, `Abbr`, `Variant`, `NumForm`. V našem poli je to
šum a jsou to nejlevnější škrty, jaké máme k dispozici.

**Atribut jako objekt.** Nejlepší myšlenka v textu — ne kvůli evidenci, ale
proto, že teprve tím jde váhy **počítat** místo hádat.

**Zdroj u každého atributu.** Máme ho fakticky už teď (UPOS/DEPREL/FEATS
z UDPipe, TYP/LEM/PTÁ ruční), jen implicitně ve skupinách. Udělat ho
explicitním je malý krok s velkou hodnotou.

## Co z návrhu měním

### Confidence: filtrovat, ne vážit

Návrh chce u každé aktivace confidence. Nerozlišuje ale mezi dvěma věcmi,
které mají zcela jiný dopad:

* **filtrovat** — zahodit aktivace pod prahem. Vektor zůstane množinou
  řetězců, shoda přesná, pole čitelné. Levné.
* **vážit** — confidence vstoupí do porovnání. Rovnost se stane věcí prahu,
  šablony přestanou být stabilní mezi dvěma rozbory téhož textu, a pole
  přestane jít přečíst okem.

Čitelnost není detail, je to podmínka, kterou držíme od začátku. Začneme
filtrováním.

### Entropii zatím nemáme na čem spočítat

Bod 19 chce vážit automaticky podle informačního zisku. Máme **86 tokenů
faktů**. Jakýkoli odhad entropie z toho je šum. Objektový model tu kolonku
ponese, ale **prázdnou**, dokud nebude korpus o dva až tři řády větší —
jinak budeme ladit na náhodě a tvářit se, že měříme.

### Hierarchie není přejmenování

Bod 20 vypadá jako konvence pojmenování, ale je to nejhlubší změna
v celém seznamu: pokud `Case=Nom` visí pod `Case` pod `Morphology`, přestane
být vektor plochou posloupností a změní se význam slova „šablona". Patří
k bodu o podobnostním slučování, ne mezi kosmetické úpravy.

## Díra, kterou návrh nepojmenoval

**Odkud se ty atributy vezmou?**

Třicet až čtyřicet ontologických tříd na každé podstatné jméno, třináct rolí
na každý argument, patnáct slovesných tříd, valenční rámce. Na osmi větách to
naklikáš; na korpusu, kvůli kterému to celé stavíme, nikdy.

Je to jediná otázka, která rozhoduje o proveditelnosti — a v návrhu chybí.

Přitom pro češtinu **velká část toho existuje** a stojí za prověření dřív, než
to začneme vymýšlet:

| co návrh chce | co už existuje |
|---|---|
| sémantické role (bod 4) | tektogramatická rovina PDT — funktory `ACT`, `PAT`, `ADDR`, `ORIG`, `EFF` |
| valence (bod 6) | VALLEX, PDT-Vallex |
| třídy sloves (bod 5) | SynSemClass |
| ontologický strom (bod 3) | Czech WordNet — hyperonymie |

Rozdíl mezi „navrhnout 40 tříd" a „napojit se na hotový zdroj" je řádový.
Náš model je z rodiny PDT-C, takže k tektogramatice je blízko.

Architektura je na to připravená: šev `ZdrojAktivaci` existuje právě proto,
aby se dalo přidat druhý zdroj aktivací vedle UDPipe, aniž by se sáhlo do
jádra.

## Katalog atributů

Beru návrh, jen doplňuju, které kolonky se dnes dají naplnit a které ne.

| kolonka | zdroj | naplnitelná dnes |
|---|---|---|
| id, skupina, nadřazený | ručně | ano |
| zdroj (UDPipe / ruční / ontologie…) | ručně | ano |
| pokrytí ve faktech, v dotazech | spočítá se | ano |
| kardinalita | spočítá se | ano |
| confidence | rozbor | ano, u UDPipe |
| stabilita | měření napříč rozbory | ano, ale potřebuje víc dat |
| informační zisk, váha | měření | **ne — korpus je o dva řády malý** |
| podobné a opačné atributy | ručně nebo z ontologie | částečně |

## Pořadí, které navrhuju

1. **Metrika** — obě čísla (strop i křížově) jako součást testů, aby každá
   další změna měla jak být vyhodnocena. Bez toho je zbylých devatenáct bodů
   nefalzifikovatelných.
2. **Katalog atributů jako objekt**, zatím jen jako evidence: skupina,
   nadřazený, zdroj, pokrytí, kardinalita. Váhy prázdné.
3. **Ubrat, ne přidat.** Vyházet `NameType`, `Style`, `Hyph`, `Foreign`,
   `Abbr`, `Variant`, `NumForm` a změřit dopad. Nejlevnější experiment
   v seznamu a odpoví na otázku, jestli je jemnost opravdu ten problém.
4. **Slučování podle podobnosti** místo přesné shody — pátý šev, který zatím
   nemáme. Teprve tímhle přestane platit, že víc atributů = horší zobecnění.
5. **Sémantické vrstvy**, napojené na existující zdroje. Až teď.
6. **Větší korpus.** Bez něj se body o entropii a vážení nedají udělat vůbec.

V původním návrhu jsou body 3 a 4 skoro na konci a bod 5 zabírá devět
z dvaceti kapitol. Podle měření to má být obráceně.

## Co zůstává otevřené

* Jaká úspěšnost je vlastně cíl? 22 % je výchozí stav při metrice, o které
  výše píšu, že měří špatně; po rozdělení na zásah pole a výběr v poli bude
  jiné a nevíme, co je dobré.
* Má se pro fakta a dotazy brát jiná sada atributů? Měření napovídá, že ano —
  nejlepší výsledek dalo `r_q=1, r_f=0`, tedy různé nastavení pro každou
  stranu. Je to na hraně šumu, ale směr sedí s tím, že otázka a fakt jsou
  různé žánry.
* Kolik z těch 54 dvojic je vůbec řešitelných? Šest otázek nemá v textu
  odpověď a jsou v sadě schválně; u zbytku nevíme, kolik je principiálně
  nejednoznačných.
