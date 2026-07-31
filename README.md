# pole2 — aktivační pole, slovník, vazby a šablony

Text i dotazy jako pole aktivací. Řádek na slovo, sloupec na aktivaci; z okolí
každého slova se skládá vektor a stejné vektory se slučují do šablon.

## První zprovoznění po klonu

`.venv/` a `models/` se neverzují — dohromady mají přes 2 GB. Zdrojáky UDPipe
jsou submodul, ne kopie. Obojí se dá obnovit:

```bash
git submodule update --init          # vendor/udpipe2-src z ufal/udpipe

python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

# model UDPipe 2 (357 MB) — adresář, ne soubor
mkdir -p models/udpipe2
cp -R …/cs_all-ud-2.17-251125.model models/udpipe2/

# RobeCzech pro embeddingy (484 MB); stáhne se i sám, když se v udpipe.sh
# vypne HF_HUB_OFFLINE
mkdir -p models/hf/hub
cp -R ~/.cache/huggingface/hub/models--ufal--robeczech-base models/hf/hub/
```

Samotný backend nic z toho nepotřebuje — bez modelu jen nepůjde rozbor vět.

## Spuštění

Dvě věci, každá ve svém terminálu:

```bash
./udpipe.sh                 # rozbor vět, port 8020
python3 -m server           # stránka a data, port 8000
```

Pak otevři **http://localhost:8000/**.

Bez UDPipe stránka funguje, jen v dialogu nové věty nepůjde tlačítko
*Rozebrat UDPipem* — atributy se dají vyplnit ručně.

Přes `file://` to **nejede**: stránka je poskládaná z ES modulů a ty prohlížeč
z lokálního souboru kvůli CORS odmítne.

## Co kde je

| | |
|---|---|
| `pole2.html` | slupka — jen odkazy na styly a `js/app.js` |
| `js/jadro/` | **výpočet.** Nezná DOM ani ukládání, testuje se bez prohlížeče |
| `js/pohled/` | kreslení mřížky, panelů, hran, zvýrazňování |
| `js/listy/` | jednotlivé listy; berou hotový model, samy nepočítají |
| `js/app.js` | jediné místo, kde se bloky skládají |
| `server/` | HTTP, JSON úložné, klient k UDPipe |
| `data/vychozi.json` | výchozí vertikály, oba korpusy a předvyplněné mapování |
| `test/jadro.mjs` | `node test/jadro.mjs` — ověří jádro na reálných datech |

Řez vede podle toho, **co která věc ví**. Když jádro začne sahat na
`document`, patří jinam; když list začne počítat, patří to do jádra.

## Jak to funguje

**Odsazení místo rámu.** Každá věta dostane `r` prázdných řádků na obou
koncích. Mezi posledním slovem jedné věty a prvním slovem druhé tak leží vždy
`2r` prázdných řádků a okno nemá jak přelézt hranici — hranici drží sama
geometrie. Co za větu přesahuje, je `∅` a ve slovníku má vlastní tvar
`<empty>`; do okolí vstupuje, středem není.

**Dva poloměry.** Fakta a dotazy mají každé své `r` a smí se lišit. Jde to
proto, že se vektory obou stran nikdy neporovnávají přímo — mapování je
kotvené na tvarech, ne na obsahu vektoru.

**Slovník je společný, šablony a vazby ne.** Že je týž tvar ve faktu i
v dotazu, samo o sobě nic nespojuje. Spojení dělá až mapování na listech
*Vazby*.

**Id šablon jsou odvozená.** `t03` je jen pořadí, v jakém vzor vznikl, a při
každé změně `r` se přečísluje. Proto se mapování ukládá jako množina tvarů a
dvojice šablon se z ní odvozuje až při kreslení — a proto má každá dvojice
poloměrů vlastní store (`data/maps/q<rq>f<rf>.json`).

**Pořadí aktivací je významné.** Vektor je řetězec, takže dvě slova s touž
sadou aktivací v jiném pořadí by dostala různé šablony. Před složením se vždy
srovnají do pořadí sloupců pole.

## Nezávislost

Vše potřebné je uvnitř adresáře:

```
vendor/udpipe2-src/     zdrojáky UDPipe 2
models/udpipe2/…model/  cs_all-ud-2.17-251125  (357 MB)
models/hf/hub/…         RobeCzech pro embeddingy (484 MB)
.venv/                  TensorFlow, transformers, ufal.*  (1,4 GB)
```

`udpipe.sh` směruje cache HuggingFace dovnitř projektu a vynucuje offline
režim, aby si nic netahalo ze sítě ani z domovského adresáře.

Ven sahá jediná věc: **interpret** `/opt/homebrew/opt/python@3.11`, na kterém
je `.venv` postavená.

Model je týž, ze kterého vznikla výchozí data — proto rozbor nové věty vrací
aktivace, které v poli už mají svou vertikálu, a nová věta nezaloží sloupec
navíc.

## API

| | |
|---|---|
| `GET /api/state` | vertikály a oba korpusy; 404 = server běží, jen nemá data |
| `PUT /api/state` | uloží totéž |
| `GET /api/maps` | všechny mapovací story |
| `GET,PUT /api/maps/q<rq>f<rf>` | mapování pro jednu dvojici poloměrů |
| `POST /api/parse` | `{"text":"…"}` → tokeny z UDPipe + seznam neznámých aktivací |

Data se ukládají zároveň do prohlížeče i na backend. Když backend neběží,
zůstane jen v prohlížeči; jakmile naběhne, práce se při dalším načtení
vytlačí nahoru.
