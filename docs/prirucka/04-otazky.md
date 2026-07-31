# 04 · Tvorba otázek a měření

Dvě sady, každá na něco jiného.

| sada | jak vznikla | co měří |
|---|---|---|
| `data/gold/otazky.json` | strojově z návěsek | **najde** systém, co v korpusu leží? |
| `data/gold/etalon.json` | rukou | **odpoví** systém, jak by se člověk zeptal? |

---

## 1 · Generovaná sada — `scripts/otazky.py`

**Princip.** Z každé věty, která má osobu a návěsku, se složí otázka
a odpověď se ví předem — je to ta návěska.

```
python3 scripts/otazky.py generuj
```

```
věta:    Roku 1934 konečně odmaturoval na nymburském gymnáziu.
kořen:   odmaturoval        entita: bohumil_hrabal
návěska: Typ=cas 'Roku 1934'
otázka:  Kdy odmaturoval Bohumil Hrabal?  →  'Roku 1934'
```

**Kontrakt.**

| funkce | role |
|---|---|
| `koren_vety(veta)` | přísudek — bez něj otázka nemá o čem |
| `entita(koren)` | `Ent=` na kořeni; bez osoby otázka nemá koho |
| `naveska_typu(veta, typ, koren)` | nález daného druhu, který patří TOMUHLE slovesu |
| `visi_na(veta, i, koren)` | závisí nález na kořeni, aniž se opustí klauzule? |
| `zvratne(veta, koren)` | „se" — jinak by vyšlo „Kde narodil Hrabal?" |
| `doplneni(veta, koren)` | neúplné sloveso bez předmětu není otázka |
| `jmeno_autora(kdo)` | `bohumil_hrabal` → `Bohumil Hrabal` |

**Dva řezy, oba z chyb:**

```python
# Životní rozpětí v závorce není odpověď na otázku po ději.
if any(a == "Udal=zivot" for a in t["acts"]):
    continue
```

*„oženil se s Marií Podhajskou ( 1859 – 1927 )"* dalo na otázku „Kdy se
oženil Jirásek?" rok narození jeho ženy. Závorka na slovese strukturně visí
(patří k podstatnému jménu, které na něm visí), takže kontrola závislosti
nepomůže — naopak by potvrdila právě tu chybnou.

```python
CIZI_KLAUZULE = ("acl", "advcl", "ccomp", "xcomp", "csubj", "conj", "parataxis")

def visi_na(veta, i, koren, max_kroku=8):
    """Chůze se zastaví, jakmile by prošla slovesem vlastní klauzule."""
```

První verze počítala KROKY (nejvýš dva) a bylo to špatné měřítko:
`Dne 12. srpna 1879 se Alois Jirásek oženil` má řetěz
`1879 → srpna → Dne → oženil`, tedy tři kroky. Předsunuté určení času tak
propadlo — a to bylo **45 % všech časových návěsek**. Proti cizí klauzuli
nechrání délka cesty, ale hranice klauzule.

*Ověřeno:* nevisících časových návěsek 45 % → 13 %, sada 540 → 682 otázek,
přesnost přitom **stoupla** na 90 % a průměr kandidátů klesl na 1,8.

**Stabilní klíč.** Položka nese `dok` a `vd` (dokument a pořadí věty v něm),
ne pozici v korpusu:

```json
{"q": "Kde pracoval Alois Jirásek?", "dok": "alois_jirásek", "vd": 1,
 "rozsah": [11], "typ": "Typ=misto", "odpoved": "Litomyšli"}
```

Pozice přežije přesně do příští přestavby. Po rozšíření z 12 na 34 článků
ukazovala jinam a měření spadlo ze 100 % na 0 %, aniž by to cokoli ohlásilo.
`nacist_zlatou(o)` klíč přeloží na pozici — na **jednom místě**, aby se
překlad nemohl tiše rozejít.

---

## 2 · Měření generované sady — `scripts/odpovedi.py`

```
python3 scripts/odpovedi.py            # skóre
python3 scripts/odpovedi.py --ukaz 6   # šest otázek rozepsaných
python3 scripts/odpovedi.py --znalost  # co přidá znalost z dialogu
```

*Ověřeno:*

```
korpus: 25 755 vět · 388 632 slov · 162 391 šablon · slovník 56 985 tvarů
vět s entitou: 4490/25755 (17 %)  ← zlatá sada je právě tenhle podíl
zlatá sada: 682 otázek

zásah pole 682/682 (100 %) · přesně 612/682 (90 %) · průměr 1,8
poctivý zápor: mlčí 5/5
```

**Ta poznámka o 17 % je podstatná.** Zlatá sada je právě ten podíl korpusu,
kde koreference uspěla — `kotvy.py` věty bez entity přeskakuje. Číslo popisuje
mechanismus na příznivém vzorku, ne pokrytí korpusu. Skript to píše sám do
hlavičky, aby se to nedalo přehlédnout.

---

## 3 · Kurátorovaná sada — `scripts/etalon.py`

**Princip.** Generovaná sada má odpověď **z konstrukce** — vznikla
z návěsek, které v korpusu leží, a všechna má tvar
`Kdy/Kde <sloveso> <jméno>?`. Nikdy se z ní nedozvíme, co se stane
u otázky, kterou by položil člověk, ani jestli systém pozná, že neví.

**Tvar položky** (převzato z etalonu conBondu):

```json
{"q": "Kolik zubů má dospělý pes?",
 "expect": ["42"],
 "mode": "answer",
 "kind": "zvířata",
 "dok": "pes_domácí"}

{"q": "Kdy se narodil Sherlock Holmes?",
 "expect": [], "mode": "unsure", "kind": "zápory", "dok": ""}
```

* `expect` je **seznam podřetězců**, ne přesný úsek. Odpověď je text v pádu,
  jaký si žádá věta („v Židenicích"), a trvat na hranici úseku znamená
  měřit tokenizaci, ne odpověď.
* `mode: unsure` je plnohodnotný režim: **stroj, který si vymyslí, je horší
  než stroj, který mlčí**.
* `mezera` (volitelně) pojmenuje známou příčinu selhání, aby nevypadalo
  jako náhodné.

**Kontrakt.**

| funkce | role |
|---|---|
| `sedi(text, ocekavane)` | podřetězcová shoda, bez ohledu na velikost písmen |
| `vyhodnotit(o, polozka)` | `{ok, prvni, duvod}`; u `unsure` je `ok` = mlčel |
| `V_POLI = 5` | kolik kandidátů se ještě počítá jako „v poli" |

**Ukázka.** *Ověřeno:*

```
doména              otázek   uspěl   první  z toho mlčet
zvířata                  9       7       4             0
životopisy               6       5       5             0
věci                     7       4       3             0
bible                    2       1       0             0
zápory                   6       6       0             6
celkem                  30      23      12             6
uspěl 77 % · první 50 %
```

**K čemu to bylo dobré hned.** Napoprvé 50 % — a rovnou ukázala, co
generovaná sada schovávala: **mimo životopisy nefungovalo skoro nic**
(věci 0/7, bible 0/2). Zúžení bylo postavené na entitách a ty existují jen
u 49 biografií. To vedlo k přepsání zúžení na vážení (viz díl 03).

**Sedm zbylých mezer je pojmenovaných:**

| mezera | proč |
|---|---|
| Co / Jaký / Jak | tázací tvar nemá druh odpovědi — umíme čas, místo, počet |
| `30 000` | rozdělené na dva tokeny, návěska je jen na `30` |
| `před 2 miliardami let` | Metron to bere jako počet, ne Chronos jako čas |
| `třicet osm` | číslovka slovy jsou dvě návěsky, ne jedna |
| rok narození Jiráska | v poli je, ale až za datem svatby — zúžení uvnitř pole |
