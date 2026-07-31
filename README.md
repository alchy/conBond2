# pole2 — aktivační pole

Text i dotazy jako pole aktivací. Řádek na slovo, sloupec na aktivaci; z okolí
každého slova se skládá vektor a stejné vektory se slučují do šablon.

**Zdroj pravdy je `core/` — knihovna v Pythonu.** Web je jeden ze dvou kanálů
k témuž jádru; druhý je `import core`. Prohlížeč nic nepočítá, model si
vyzvedne.

## Spuštění

```bash
python3 -m server start      # UDPipe (9010) i web (9000)
python3 -m server status
python3 -m server stop
```

Pak **http://localhost:9000/**. Porty a cesty jsou v `config.json`.

Přes `file://` to nejede: stránka je z ES modulů a bez backendu nemá odkud
vzít model.

## Knihovna

```python
from core import Pole, UlozisteSouboru, nastavit_log

nastavit_log(uroven="info")
pole = Pole(UlozisteSouboru("data"))
pole.nastaveni.polomer_dotazu = 4     # nastaví se jednou a platí
pole.postavit()
print(pole.dotazy.pocet_sablon(), "šablon dotazů")
```

Poloměr se nevleče každým voláním — drží ho `Nastaveni`. Setter jen poznamená,
že model zestaral; přepočítá se, až si o výsledek někdo řekne.

### Workflow a třídy

| krok | třída | soubor |
|---|---|---|
| rozprostřít věty a odsadit | `Tok` | `core/flow.py` |
| určit sloty kolem středu | `Okno` | `core/window.py` |
| sdílený slovník tvarů | `Slovnik` | `core/lexicon.py` |
| šablony a vazby jedné strany | `Strana` | `core/side.py` |
| celý průchod | `Pole` | `core/field.py` |
| složit otázku ze slovníku | `Skladac` | `core/compose.py` |

### Čtyři švy

Vyměnitelné, aniž by se sáhlo do jádra — `core/interfaces.py`:

| šev | co se dá vyměnit |
|---|---|
| `ZdrojAktivaci` | odkud se berou atributy tokenu |
| `Uloziste` | odkud se čte korpus a kam se ukládá |
| `SkladacVektoru` | jak se z okolí udělá vektor |
| `Slucovac` | kdy jsou dva vektory tatáž šablona |

Když se v jádře objeví `if` podle druhu dat, znamená to, že tam šev chybí.

## Data

Každý datový typ má svou složku, všechno JSON a čitelné okem:

```
data/
├── verticals/verticals.json   sloupce pole
├── corpora/facts.json         věty textu
├── corpora/query.json         dotazy
├── mappings/q1f1.json         dvojice pro JEDNU dvojici poloměrů
└── defaults/                  zdrojová sada, ze které se zakládá
```

`Config` je umí přesměrovat jinam — pro testy, pro druhý korpus:

```python
Pole(UlozisteSouboru(config=Config(data="/tmp/zkouska")))
```

## Log

Dvě úrovně, každá pro něco jiného:

* **info** — že průchod probíhá a kudy. Třináct řádků na celý průchod.
* **debug** — co, jak, ve které metodě a s jakým výsledkem. Rozsáhlý schválně:
  smyslem je dát se na ten výstup pověsit a číst chování zpětně.

```
09:35:53 INFO  › průchod  r_f=1 r_q=4
09:35:53 INFO  slovník hotov  tvaru=104 v_obou=38 nejistych=20
09:35:53 DEBUG side.Strana.zaradit_stred  střed zařazen  radek=1 tvar=karel sablona=t01
```

Jméno metody se doplňuje ze zásobníku, takže se nemůže rozejít s tím, kde
opravdu je. Nastavuje se v `config.json` (`log_uroven`, `log_soubor`).

## Jak to funguje

**Odsazení místo rámu.** Každá věta dostane `r` prázdných řádků na obou
koncích. Mezi sousedními větami tak leží `2r` prázdných řádků a okno nemá jak
přelézt hranici — drží ji sama geometrie. Co přesahuje, je `∅` a ve slovníku
má tvar `<empty>`; do okolí vstupuje, středem není.

**Dva poloměry.** Fakta a dotazy mají každé své `r` a smí se lišit, protože se
vektory obou stran nikdy neporovnávají přímo — mapování je kotvené na tvarech.

**Slovník je společný, šablony a vazby ne.** Že je týž tvar ve faktu i
v dotazu, samo o sobě nic nespojuje.

**Id šablon jsou odvozená.** `t03` je jen pořadí vzniku a s každou změnou `r`
se přečísluje. Proto se mapování ukládá jako tvary a pořadí, a proto má každá
dvojice poloměrů vlastní store.

**Tázací tvar je vlastní vertikála.** UD ho nerozliší: `jak`, `kdy`, `kam`,
`kde` a `proč` mají jeden a týž podpis, takže pět sémanticky nejvzdálenějších
otázek by spadlo do jedné šablony. Lemma nestačí — `co` a `koho` se ptají na
různé věci, ale lemma mají totéž.

**Pořadí aktivací je významné.** Vektor je posloupnost, takže táž sada jinak
seřazená by dala jinou šablonu; před složením se vždy srovná do pořadí sloupců.

## Testy

```bash
python3 test/core.py
```

Bez prohlížeče i bez serveru — jen import knihovny.

## Nezávislost

Vše potřebné je uvnitř adresáře:

```
vendor/udpipe2-src/     submodul ufal/udpipe
models/udpipe2/…        cs_all-ud-2.17-251125  (357 MB)
models/hf/hub/…         RobeCzech pro embeddingy (484 MB)
.venv/                  TensorFlow, transformers, ufal.*  (1,4 GB)
```

`udpipe.sh` směruje cache HuggingFace dovnitř projektu a vynucuje offline
režim. Ven sahá jediná věc: interpret, na kterém je `.venv` postavená.

Po klonu:

```bash
git submodule update --init
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
# model a RobeCzech se kopírují zvlášť, viz models/
```

## API

| | |
|---|---|
| `GET /api/field?rf=&rq=&syrove=&stred=&typy=` | celý model pro dané nastavení |
| `GET,PUT /api/data` | vertikály a oba korpusy |
| `GET,PUT /api/mappings/q<rq>f<rf>` | mapování pro dvojici poloměrů |
| `POST /api/compose` | vektor složené otázky |
| `POST /api/parse` | věta → tokeny z lokálního UDPipe |
