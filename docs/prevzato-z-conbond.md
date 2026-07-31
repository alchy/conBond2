# Co převzít z conBondu

Studie 27 modulů `conbond/core/`. Jejich docstringy nesou naměřené závěry, ne
záměry — proto stojí za čtení i teď, když stavíme jinak.

**Co je jinak.** conBond vytěžoval FAKTY (predikát + role) a odpovídal
predikátovým matchem. My stavíme POLE a odpovídáme šablonou. Řada jeho
závěrů je proto o vrstvě, kterou nemáme. Ale příprava textu, identita a
pasti jsou společné — text je týž a chyby taky.

---

## 1 · Převzato hned: biografická závorka

`bio.py`. Změřeno u nás: **200 vět má závorku s rokem a všech 200 nemělo
jedinou časovou návěsku.** Přitom je to úvodní věta každého článku a nese
narození i úmrtí naráz.

```
Alois Jirásek ( 23. srpna 1851 Hronov – 12. března 1930 Praha ) byl…
                └── narození ──┘        └── úmrtí ─────┘
```

Chronos závorky přeskakuje a je to **správně** — bez toho řezu přivěsil roky
rodičů k narození protagonisty. Nový `core/agents/bio.py` ten řez neruší, jen
tuhle jednu konstrukci čte záměrně. Přineslo to 850 návěsek, z toho 47
narození a 46 úmrtí.

Dvě pasti, na které jsem cestou přišel a obě jsou v kódu popsané:

* **Ne každá závorka za jménem je životopis.** První verze přivěsila
  „narození" datům manželky, dcery i létům studia. Narození a úmrtí se teď
  přiznají jen u definiční věty (jméno na začátku + spona za závorkou);
  jinde je to `Udal=zivot` — čas a místo ano, čí život nevíme.
* **Ne každá pomlčka dělí.** „( 1926 Praha - Libeň – 2011 Praha )" má
  pomlčky dvě a spojovník uvnitř názvu čtvrti udělal z Libně místo úmrtí.
  Dělí en-dash, a z kandidátů ten, co má rok na obou stranách.

---

## 2 · Co převzít dál, v pořadí podle užitku

### `clusters.py` — přivěšení holé zmínky

Bare jméno („Vítězslav") se rozdělí **per dokument** a přivěsí k plnému
jménu, které v TOM dokumentu žije. Právě jeden kandidát → merge; víc →
ambiguita, nechat být.

**Proč to potřebujeme:** našel jsem 85 vět, kde je podmětem známý autor bez
entity, a všechno jsou křestní jména (*jan, josef, františek, karel*).
Navázat je globálně by vrátilo chybu, kterou projekt už popsal — „fakt
navěšený na Karel patřil všem sedmadvaceti Karlům". **Per dokument** je
jednoznačné a bezpečné.

### `names.py` — kdy jsou dva zápisy týž člověk

Dvě pravidla, obě z měření: **titul do jména nepatří** a **kratší tvar se
bere jako předpona delšího** (lemmatizace vlastních jmen kolísá — „Čapk" ×
„Čapek"), od čtyř znaků, aby „Jan" nesplynulo s „Jana".

### `normalize.py` — oprava tokenizace na JEDNOM místě

Tečkované zkratky („R.U.R." → R/./U/./R/.) se opravují na jediném
chokepointu, takže korpus i otázky projdou týmž kódem. **My máme
`sceli_zkratky` jen v mluvnici tvrzení, na korpus se nepouští.** Patří to do
rozboru.

### `health.py` — mrtvá data přestanou být tichá

Raw soubor novější než jeho shard = anotace neproběhla. Chybějící index,
přestavba zastavená v půlce. Jen čte a hlásí.

**Právě jsem na to doplatil:** po přestavbě korpusu spadla zlatá sada
ze 100 % na 0 %, protože odkazuje na POZICE vět a korpus má teď 7508 vět
místo 3478. Nic to neohlásilo — jen se změnilo číslo.

### `provenance.py` — z čeho ta vrstva vznikla

Otisky obsahu, ne ruční čísla verzí (zastarají), bez časové známky (git drží
„kdy", soubor „z čeho"). Tři otisky, protože se mění nezávisle: parser,
mapování rolí, resolver.

### `datafiles.py` — chybějící soubor je normální, poškozený není

Tichý návrat prázdna se projeví až chudšími odpověďmi a hledá se mnohem hůř.

---

## 3 · Co NEpřebírat, a proč

**`fact_store.py` — parent-model matching.** Jeho závěr je ale varování,
které platí i pro nás:

> Window-VZOR vidí jen lokální okno, takže otázku a fakt nesouměří: „Kde se
> narodil X" (okno kolem frontovaného „Kde") ≠ „Narodil se v Y" (okno kolem
> místa uprostřed).

To je přesně naše situace a je to důvod, proč náš odpovídač **šablony vůbec
nepoužívá** — spojuje přes entitu a tvar slovesa. conBond na to nasadil
predikát jako most. My máme mapování šablon, ale ruční. Tohle je nedořešené
místo, ne převzatá věc.

**`grammar.py`** říká něco, co je v napětí s našimi hrubými vrstvami:

> VZOR je přesný na gramatiku, ale abstraktní na lexém; pokrytí se získává
> KVANTITOU přesných vzorů, ne rozmazáním jednoho.

Naše `SitkoStupnovane` dělá pravý opak — rozmazává, aby se sdílelo. Obojí je
změřené na jiné úloze, takže to není spor, ale stojí za to vědět, že to jde
proti sobě.

**`reldefs.py` — definiční rekurze.** „Tchán ≡ otec manžela či manželky" se
z definiční věty v korpusu odvodí jako pravidlo a odvozené hrany se
materializují při buildu; runtime se nemění. To je zobecnění toho, co dělá
náš dialog, a je to hotové. Až budeme mít vztahy hlubší než `⊂`, je tohle
vzor, podle kterého to postavit.

---

## 4 · Třída importéru: ano, a takhle

Dnes je celý příjem v `scripts/baseline.py` jako funkce. Podle vlastního
pravidla projektu („zdroj pravdy na backendu, knihovna, ne monolit") patří
do `core/` jako stavební bloky:

```
core/ingest.py
    Import       syrový text → věty        (+ normalizace na chokepointu)
    Rozbor       věty → tokeny             (sjednotit se server/parse.py —
                                             dnes jsou dva klienti UDPipe)
    Koreference  doplnění podmětu          (+ per-doc přivěšení holé zmínky)
    Vypovedi     próza / seznam            (už hotové jako oznacit_druh)
    Prijem       fasáda: raw → korpus
```

Dvě věci, které to má srovnat hned:

* **Dva klienti UDPipe.** `scripts/baseline.py:rozebrat()` a
  `server/parse.py:Rozbor` dělají totéž jinak. Jeden z nich normalizaci
  zkratek nemá — a to je přesně ta tichá odchylka, na kterou `normalize.py`
  upozorňuje.
* **Zlatá sada na pozicích.** Odkaz `{"veta": 6}` přežije jen do příští
  přestavby. Potřebuje stabilní klíč — dokument + pořadí ve větě, jako to
  má conBond ve `factlink.py` (`KEY` definovaný na jednom místě, protože
  ho čte pět míst a rozešel by se tiše).
