# Zadání: vzor identifikuje větu, graf zaměří odpověď

Stav k `0dd9494`. Testy zelené, etalon 40 otázek **85 % uspěl · 65 % první**,
scénáře 2/2. Korpus 26 051 vět, 485 570 tokenů, 91 dokumentů.

Tenhle dokument není shrnutí hotového. Je to **zadání na přestavbu
odpovídací cesty** a popis toho, proč je potřeba.

---

## 1 · Diagnóza: odpovídač nepoužívá to hlavní

```
$ grep -n "sablon\|vzor" core/answers.py
(nic)
```

Odpovídač nesahá na šablony **ani jedním řádkem**. Stojí na třech
rejstřících:

| rejstřík | co obsahuje | čím je |
|---|---|---|
| `podle_tvaru` | tvar → věty | seznam výskytů slova |
| `podle_entity` | dokument → věty | **pytel vět o osobě** |
| `podle_typu` | věta → typ → rozsahy | co našli agenti |

Graf (`core/graph.py`) se používá **jen** na otázku „mohl A znát B?".
Nikde jinde.

Centrální abstrakce projektu — šablona, tedy skupina vět se stejným
vektorem — se odpovídání neúčastní.

### Proč to vadí, na jednom případu

```
Kde byl Jan uvězněn?   →   Praha
```

Praha je z článku o Janu Nerudovi. Rozklad:

```
tvary z otázky:   jan, uvězněn
entita:           jan_neruda        (z pěti Janů; vyhrál, protože má rok narození)
„uvězněn" svítí:  5 vět             (jinde v korpusu, ne u Nerudy)
průnik:           0 vět             ← pole je PRÁZDNÉ
rozšíření:        celý článek o Nerudovi
odpověď:          první Typ=misto, na které se narazí
```

**Pytel vět Prahu obsahuje. Vzor ani hrana ne.** Proto se to laděním vah
nespraví: Praha tam *je*, jen nepatří k té otázce, a váha ten rozdíl
nevidí.

Jan Křtitel je v korpusu jako **zmínka**, ne jako dokument. Dokud entita
znamená dokument, budou se biblické postavy mapovat na spisovatele.

---

## 2 · Zadání

### 2.1 Otázka se převede na VZOR, ne na množinu slov

Dnes: `obsahove_tvary()` → seznam slov → věty, kde ta slova leží.

Má být: otázka se rozebere, složí se z ní vektor týmž skládačem jako věty
korpusu, a hledají se věty **téže šablony**.

```
„Kde byl X uvězněn?"   →  vzor vět typu „<osoba> byl uvězněn v <místo>"
                       →  žádná taková věta o Janovi neexistuje
                       →  MLČENÍ
```

Infrastruktura existuje: `Skladac`, `Slucovac`, dotazová strana pole
(`pole.dotazy`) a mapování mezi stranami se staví, jen se z něj neodpovídá.
Šablona je „abstrakce, která má matchnout kandidáty" — ne ranker. To je
podstatný rozdíl; viz oddíl 5.

### 2.2 Zásah je HRANA, ne spoluvýskyt

Odpověď musí viset na téže hraně jako událost z otázky. Ne „místo, které
se vyskytuje v článku o té osobě", ale „místo připojené k té události".

`core/edges.py` hrany už vyrábí (`hrany_z_korpusu`), ale odpovídač je
nepoužívá. Nad celým korpusem jich je **163 na 92 predikátů** — málo;
konstrukce bere jen jmenný přísudek s genitivem a sloveso s předmětem,
obojí s oběma konci jako vlastní jméno. Rozšířit ji je součást zadání.

### 2.3 Váhy z toho vypadnou

Nemá se rozhodovat, jestli `bible_1_jan` váží víc než `jan_neruda`, když
se ptáme na vzor a hranu.

---

## 3 · Co existuje a na čem se dá stavět

| modul | co umí | používá odpovídač? |
|---|---|---|
| `core/roles.py` | větné členy z rozboru, 12 rolí | ano, jako záchranná síť |
| `core/edges.py` | hrany z korpusu + slučování jmen | **ne** |
| `core/graph.py` | vážený graf osob, cesty s doložením | jen „mohl znát" |
| `core/relations.py` | pravidla z definic i z faktů, fixpoint, arita | **ne** |
| `core/diagram.py` | šipkový diagram, modus ponens/tollens, modely | **ne** |
| `core/dimensions.py` | rozměr vylučuje, nepotvrzuje; měření značek | **ne** |
| `core/cas.py` | životy z korpusu, osa času | jen „mohl znát" |
| `core/tabulka.py` | přiřazovací úlohy, „právě jeden" | **ne** |

Ověřeno samostatně (viz `test/core.py`, `scripts/diagram.py`):

* definiční text → **15 pravidel**, fixpoint přijme 14 (`pravnuk` až po `vnuk`)
* vztahový text → **7 hran ze 7**, po sloučení jmen odvodí `děd`, `strýc`,
  `teta` — věty, které v textu nestojí
* šipkový diagram vyřeší tři úlohy z Bartlové (věštkyně, vnuk, večírek)
* čas jako rozměr: 16 doložených dvojic, 0 disjunktních, pozadí 20,3 % —
  vzorec sedí, ale práh 20 dokladů se **neohnul**, takže se pravidlo nepřijalo

---

## 4 · Otevřené vady

1. **Entita = dokument.** „Kdo byl Jan?" → Jan Neruda, „Kde byl Jan
   uvězněn?" → Praha. Vrstva osob (`podle_jmena`, 1519 jmen) existuje, ale
   entita se pořád bere z názvu článku.
2. **Holé příjmení je v grafu vlastní uzel** — cesta začíná
   `bohumil hrabal → hrabal`.
3. **Životy má jen 26 osob z 39.** Rozměr času tím zůstává pod prahem.
4. **Hran je 163.** Na indukci pravidel nad korpusem to nestačí (vyjde 0);
   na vztahovém textu funguje, takže vada je v pokrytí konstrukce.
5. **`Čí?` odpoví „z Boha"** — řetěz přes předchozí odpověď funguje, ale
   výběr uvnitř zúženého pole je slabý.

---

## 5 · Čeho se vyvarovat

Zapsáno proto, že se to během jednoho dne stalo víckrát.

**Neměřit šablonu jako ranker.** Byla vyzkoušena jako řadič kandidátů,
vyšlo 81 % proti 86 % a bylo to uzavřeno jako „nefunguje". Byla to špatná
otázka: šablona má kandidáty **matchnout**, ne mezi nimi vybírat. Ten
výsledek není verdikt o tomhle zadání.

**Neladit váhy, když chybí struktura.** Poslední půlhodina práce před
sepsáním tohoto dokumentu: skóre entit, ošetření remízy, pojistka na
rozšíření, nesvítící slovo. Tři ze čtyř vráceny. A dvě z nich si vzájemně
vypnuly účinek — preference člověka zrušila remízu dřív, než ji pojistka
na remízu stihla vidět.

**Nula je nejnebezpečnější hodnota.** „Data to nemají" a „nepodařilo se
zeptat" vypadají stejně. Stalo se dvakrát: prázdný výsledek stažení se
uložil do paměti jako „pojem bez hran", a nesedící klíč v grafu vypadal
jako „žádné doložené dvojice".

**Měřit dřív než stavět.** Ráno vznikla vrstva a měřila se až potom —
skončilo to přiznáním, že ukázka byla vydávána za výsledek. Odpoledne se
nad CommonsenseQA nepostavilo nic a za dvě hodiny bylo jasné, že by to
nefungovalo, včetně důvodu.

**Když si v jádře píšu `if` podle druhu dat, chybí šev.** Časové porovnání
bylo napsané ručně (`if za < nb`), místo aby bylo zakódované jako rozměr.
Viz `core/interfaces.py`.

---

## 6 · Jak měřit

```bash
python3 test/core.py              # jádro, bez sítě
python3 scripts/etalon.py         # 40 kurátorovaných otázek + scénáře
python3 scripts/etalon.py --detail
python3 scripts/etalon_conbond.py # 95 otázek ze starého conBondu
python3 scripts/diagram.py        # šipkový diagram krok za krokem
python3 scripts/csqa.py 25        # CommonsenseQA přes ConceptNet
```

Etalon hlásí dvojici, ne jedno číslo: **uspěl** (odpověď je mezi kandidáty)
a **první** (je na prvním místě). Zúžit se ztrátou dosahu není pokrok.

Přestavba odpovídací cesty musí u každého kroku ukázat obojí — a zvlášť
u domény `zápory`, kde je správná odpověď mlčení.
