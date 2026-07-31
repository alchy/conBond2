# 05 · Zaměření tématu — na co se právě dívám

Korpus má 25 755 vět a 440 142 řádků. Celý model je **28 MB v jedné
odpovědi** a prohlížeč z toho neudělá nic. Tenhle díl je o tom, jak se
z něj dívat na kousek, aniž by čísla začala lhát.

---

## 1 · Výřez — `Vyrez` a `Prevod`

**Princip.** Pole se staví **celé**. Kdyby se stavělo z výřezu, přestaly by
být šablony šablonami korpusu a sdílení by se počítalo z náhodného vzorku —
přesně ten omyl, kvůli kterému kdysi vyšel poměr 0.95. Ven jde jen okno vět.

```python
from core import Vyrez, pole_ven
ven = pole_ven(pole, s_korpusy=True,
               vyrezy={"f": Vyrez(od_vety=0, vet=25), "q": Vyrez(0, 25)})
```

*Ověřeno:*

| co | velikost |
|---|---:|
| celý model | 28,3 MB |
| výřez 25 vět | 0,7 MB |
| výřez 10 vět | 0,4 MB |

**Čísla zůstávají globální.** Výřez se hlásí zvlášť:

```json
"cisla": {"radku": 440142, "sablon": 162391, "vet": 25755,
          "vyrez": {"od_vety": 0, "vet": 10, "radku": 186, "cely": false}}
```

Prohlížeč pak napíše `10 z 25 755 vět · 186 z 440 142 řádků`. Kdyby se
čísla přepočítala na výřez, vypadalo by to, že korpus je malý a všechno se
sdílí.

**Přečíslování.** Indexy se převedou na výřez, aby prohlížeč pracoval
s hustými poli a o okně nemusel vědět. Dělá to **jedna třída**:

```python
class Prevod:
    """Kdyby si to řádky, věty, šablony, vazby a slovník počítaly každý
    sám, stačilo by jedno místo zapomenout a hrany by ukazovaly vedle."""
    def radek(self, i): ...          # globální → místní, nebo None
    def veta(self, s): ...
    def prosit_radky(self, indexy): ...   # jen ty uvnitř, přečíslované
```

Slot mířící ven z výřezu jde jako `null` — prohlížeč pozná, že tam něco je,
jen to nevidí.

**Velikost vzoru se výřezem nemění.** U každé šablony jde ven i `celkem_tvaru`
a `celkem_radku`: že vzor sdílí 189 slov, je ta podstatná informace a oknem
se nemění.

---

## 2 · Přehled vzorů — `prehled_sablon()`

**Princip.** Mřížka se u 440 tisíc řádků vykreslit nedá a nemá to smysl ani
zkoušet. Šablona ale řádky nepotřebuje: čte se z vektoru a ze seznamu tvarů,
které ji sdílejí. Přesně to je na velkém korpusu ta zajímavá věc.

```python
prehled_sablon(strana, od=0, pocet=60, razeni="velikost", hledat="")
# → {"celkem": 162391, "od": 0, "sablony": [...], "razeni": "velikost"}
```

| řazení | podle čeho |
|---|---|
| `velikost` | kolik různých tvarů vzor sdílí ← výchozí |
| `vyskyty` | kolik má výskytů |
| `delka` | délka vektoru |
| `id` | abecedně |

**Ukázka.** *Ověřeno* — hledání `praze` dá 35 šablon z 26 624 a všechny
mají tentýž tvar:

```
f232   80 tvarů   ADP · case · Case=Loc · AdpType=Prep · Trida=pomocny
       babičce · barikádách · bavořích · benešově · brně · cizině · dobříši
```

Pole si samo vyrobilo slot „kde se to stalo" — nikdo mu neřekl, že tohle
jsou místa; vyšlo to z toho, že stojí na stejném místě věty.

---

## 3 · Domény — `scripts/domeny.py`

**Princip.** Korpus byl dlouho jen životopisy, takže šablony mohly být
tvarem životopisu, ne tvarem češtiny. Teprve druhé téma to rozhodne.

```
python3 scripts/domeny.py
```

| pojem | co počítá |
|---|---|
| vlastní vzory | šablony, které má doména jen sama pro sebe |
| sdílené vzory | šablony žijící ve víc doménách naráz |
| **přenos** | podíl slov domény, jejichž vzor zná i jiná doména |

**Ukázka.** *Ověřeno*, 86 dokumentů:

```
doména        slov     vzorů   jen svých   sdílených   přenos
bible       189 717    87 023      71 773      15 250    42,9 %
zvířata      27 750    18 536       9 412       9 124    63,4 %
životopisy  171 165    79 992      62 115      17 877    47,8 %

vzory ve VŠECH třech doménách naráz: 4069
```

**Skoro polovina slov Nového zákona** — archaická čeština, přímá řeč, žádný
encyklopedický rám — padne do vzoru postaveného na Wikipedii. To je zatím
nejsilnější doklad teze o podhoubí: že se tematický základ postaví jednou
a každý další text jím projde.

> **Licence.** Biblický text je ekumenický překlad, tedy chráněný, a je
> v `.gitignore`. Do repozitáře by patřila jen Kralická, která je volné dílo.

---

## 4 · Kontrola zdraví — `core/health.py`

**Princip.** Za jediný den se staly tři tiché vady a ani jedna se
neohlásila:

| vada | jak se projevila |
|---|---|
| přejmenované styly | stránka se vykreslila, jen bez formátování |
| nespuštění agenti | zápis korpusu je mlčky smazal |
| zlatá sada na pozicích | po přestavbě měřila jinde, 100 % → 0 % |

Všechny tři mají týž tvar: **A se změnilo, B o tom neví.**

```python
from core.health import zkontrolovat
for n in zkontrolovat(config):
    print(n)     # ✗ korpus nemá ani jednu návěsku agentů — …
```

| kontrola | co hlásí |
|---|---|
| `korpus_je()` | poškozený nebo prázdný korpus |
| `rozbor_je_cerstvy()` | syrový text novější než korpus = příprava neproběhla |
| `agenti_probehli()` | korpus bez jediné návěsky |
| `vertikaly_pokryvaji()` | aktivace bez sloupce — v poli není vidět |
| `zlata_sedi_na_korpus()` | chybí stabilní klíč, nebo se otázky nenašly |
| `styly_existuji()` | odkaz ze stránky na soubor, který není |

**Jen čte a hlásí.** Nic neopravuje: oprava by musela hádat, co kdo
zamýšlel, a tichá oprava je horší než tichá vada. Běží při startu serveru.

---

## 5 · Jazykový profil — `core/language.py`

**Princip.** Česká slova patří do dat, ne do podmínek. `core/grammar/cs.json`:

```json
{"spona": [" je ", " jsou "],
 "znacky_podtridy": ["je druh", "patří mezi", "spadá pod", …],
 "tazaci_na_typ": {"kdy": "Typ=cas", "kde": "Typ=misto", "kolik": "Typ=pocet"},
 "velke_pismeno_je_instance": true,
 "mesice": {"leden": 1, "ledna": 1, …}}
```

**Co sem NEpatří.** Hlášky pro člověka („přijato:", log) — je to jiná osa
a smíchat je znamená překládat log, aby šel číst dotaz. A `UPOS`/`DEPREL` —
Universal Dependencies jsou univerzální a `NOUN` není české slovo.

**Co profil neumí.** Nedělá z toho vícejazyčný program. Kromě slov se liší
i **pravidla**: „velké písmeno = vlastní jméno" platí v češtině a v němčině
je k ničemu. Takové pravidlo je proto příznak, ne seznam.

**Skutečný zisk** není angličtina, ale že přidat značku jde bez sahání do
Pythonu — `spadá pod` je jen v JSON a funguje.
