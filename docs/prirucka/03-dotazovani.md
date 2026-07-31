# 03 · Dotazování — z otázky odpověď

```python
from core import Odpovidac
o = Odpovidac(pole)
v = o.odpovedet("Kde se narodil Bohumil Hrabal?")
v["odpoved"]      # 'Židenice'
v["kandidati"]    # [{veta, rozsah, text, kontext}, …]
v["aktivace"]     # co se rozsvítilo a proč
```

---

## Dva kanály, protože se v poli chovají jinak

**Princip.** Otázka se rozloží a každý kus se hledá tím kanálem, kterým se
v poli chová.

| kus otázky | kanál | proč |
|---|---|---|
| **osoba** | aktivace `Ent=` | ve větě jako slovo většinou vůbec není |
| **sloveso a zbytek** | tvar ve slovníku | slovo tam stojí |
| **tázací tvar** | `Jazyk.na_co_se_pta()` | řekne, jaký DRUH místa hledat |

**Proč to není jinak.** První verze hledala všechna slova otázky ve
slovníku a dala **1 %**. Důvod:

```
otázka:  Kde se narodil Bohumil Hrabal?
věta 6:  Narodil se na brněnském předměstí Židenice ( Balbínova ul. 489/47…
```

**Ve 169 ze 170 zlatých vět jméno z otázky vůbec není.** Čeština podmět
zahazuje a identita sedí jako aktivace `Ent=bohumil_hrabal`, kterou doplnila
koreference. Přes aktivaci: **100 %**.

---

## 1 · Rejstříky — postaví se jednou

| metoda | co staví |
|---|---|
| `_sestavit_navesky()` | věta → typ → rozsahy, které agenti označili |
| `_sestavit_entity()` | entita → věty, ve kterých o ní je řeč |

`_sestavit_navesky()` **vynechá `Udal=zivot`**: „oženil se s Marií
Podhajskou ( 1859 – 1927 )" nese čas, ale je to rok narození jeho ženy.

---

## 2 · Rozsvícení — `rozsvitit()`

**Princip.** Pole se **váží, neproniká**.

```python
skore = defaultdict(int)
for vety_slova in zname.values():   # bod za každé slovo otázky ve větě
    for vi in vety_slova:
        skore[vi] += 1
for vi in vety_entity:              # bod za entitu
    skore[vi] += 1
nej = max(skore.values())
prunik = {vi for vi, n in skore.items() if n == nej}
```

**Proč ne průnik.** Průnik VŠECH obsahových slov je křehký:

* „Kam odešel Ježíš s matkou a učedníky?" má čtyři slova, každé svítí ve
  stovkách vět, a průnik všech čtyř je **prázdný** — přitom taková věta
  v korpusu je.
* „Kde leží sopka Ol Doinyo Lengai?" — entita článku (*sopka*, 115 vět)
  převálcovala konkrétní jméno (3 věty).

**Dva řezy, bez kterých to vymýšlí:**

```python
# 1) Cizí jméno = nevím
jmena = self.jmena_v_otazce(text)
cizi = bool(jmena) and not self.sedi_cele_jmeno(jmena, entita) \
    and any(not self.vety_tvaru(j.lower()) for j in jmena)

# 2) Když se žádné dva signály nepotkají, je to nevím — ne sjednocení
if signalu >= 2 and nej < 2:
    prunik = set()
```

*Ověřeno*, co to spravilo:

| otázka | bez řezu | s řezem |
|---|---|---|
| Kdy se narodil Sherlock Holmes? | `25. září 1916` | mlčí |
| Kde zemřel Napoleon Bonaparte? | `Praze` | mlčí |
| Kdy zemřela Marie Curie? | `roce 1896` | mlčí |
| Kdy se narodil pes domácí? | `25. září 1916` | mlčí |

Poslední dvě stály za zvláštní pozornost. *Marie Curie* trefila
`marie_majerová` přes křestní jméno — proto musí sedět **celé** jméno,
je to táž past jako „Karel patřil všem sedmadvaceti Karlům", jen na
vstupu. A *pes domácí* měl entitu (76 vět) i sloveso (67 vět), které se
nikde nesešly; bez druhého řezu se pole složilo ze všech 143 a odpovědělo
datem narození Hrabalova bratra.

**Kontrakt.**

| metoda | bere | vrací |
|---|---|---|
| `obsahove_tvary(text)` | otázka | slova, která o obsahu něco říkají |
| `najit_entitu(tvary)` | slova | klíč entity, nebo `""` |
| `jmena_v_otazce(text)` | otázka | slova s velkým písmenem mimo první |
| `sedi_cele_jmeno(jmena, entita)` | obojí | sedí VŠECHNA jména na jednu entitu? |
| `vety_tvaru(tvar)` | tvar | množina vět faktů, kde svítí |
| `rozsvitit(text)` | otázka | `{tvary, entita, svitici, nezname, cizi_jmeno, siroko, vety}` |

---

## 3 · Rozšíření znalostí — `rozsirit()`

**Princip.** Vztahy z dialogu se čtou **až při porovnání**, ne v datech.
Otázka smí zobecňovat: kdo se ptá na spisovatele, míří i na Hrabala,
protože `hrabal ∈ spisovatel`. Fakt zobecňovat nesmí — kdyby se expandovalo
do dat, vektor se prodlouží a sdílení klesne.

```python
for potomek in self.znalost.potomci(tvar.lower()):
    klic = self.najit_entitu(potomek.split())
    if klic:
        vety |= self.podle_entity[klic]     # přes ENTITU
    else:
        for kus in potomek.split():
            vety |= self.vety_tvaru(kus)    # až pak přes tvar
```

**Ukázka.** *Ověřeno* — tři věty dialogu udělaly z otázky, která nezasáhla
nic, otázku přes tři autory:

```
přijato: hrabal ∈ spisovatel · čapek ∈ spisovatel
         seifert ∈ spisovatel · spisovatel ⊂ člověk

Kde se narodil spisovatel?    bez znalosti   0 vět,   0 kandidátů
                              se znalostí  123 vět,  33 kandidátů
                              → Židenice · Nymburce · Praze
```

---

## 4 · Odpověď — `odpovedet()`

```python
typ = self.jazyk.na_co_se_pta(text)      # Kdy → Typ=cas
nalezy = self.sebrat(vety, typ)          # úseky toho druhu v poli

# Zúžení, které nic nenajde, je horší než širší pole — ale jen když
# otázce rozumíme celé.
lze_rozsirit = (akt["vet_entity"] and not akt["cizi_jmeno"]
                and not akt["nezname"])
if not nalezy and lze_rozsirit:
    nalezy = self.sebrat(vsechny_vety_entity, typ)
```

**Proč ta podmínka.** „Kdy se narodil Alois Jirásek?" protnulo entitu se
slovesem na jedinou větu a ta žádný čas neměla — rok narození stojí
v úvodní závorce, kde slovo „narodil" není. Tam se rozšířit vyplatí.
Ale u „Kolik měl Hrabal **letadel**?" by z „nevím" vzniklo „tady máš něco
o té osobě", což je zase vymýšlení, jen opatrnější.

---

## 5 · Dva stupně měření

**Šablona neidentifikuje jednu odpověď, ale DRUH místa, kde odpověď leží.**
„Kde se narodil X?" má trefit rodiště u všech autorů naráz.

```
zásah pole   je odpověď mezi kandidáty?   ← tohle dělá aktivační pole
zúžení       je první?                    ← tohle pole nedělá
```

*Ověřeno*, 682 generovaných otázek nad 25 755 větami:

```
zásah pole 682/682 (100 %) · přesně 612/682 (90 %) · průměr 1,8 kandidáta
```

**Zásah pole sám o sobě nic neznamená.** Vrátit všechno dá taky 100 %.
Musí se hlásit spolu s velikostí pole — proto je průměr kandidátů vedle.
