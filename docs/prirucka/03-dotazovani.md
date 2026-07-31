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

## 4b · Role — když žádný agent typ nedodá

Čtyři agenti umějí čtyři druhy odpovědí: čas, místo, počet, druh. Otázka,
která se ptá na něco jiného, propadla celá — a přitom to v datech leží,
protože rozbor u každého tokenu říká, jaký je to větný člen.

```
role   FUNKCE   „který větný člen to je"   z rozboru, tabulkou v cs.json
typ    OBSAH    „je to čas / místo"        našel agent
```

`Řekl jim` je `obl` v dativu ⇒ role `komu_cemu`. Nikdo to netypoval, ale
tázací tvar „Komu" na tu roli ukazuje, takže se odpověď dá vzít.

```python
# core/roles.py
def role_tokenu(self, token, veta=()):
    tabulka = self.jazyk.deprel_na_roli.get(deprel(token))
    if not tabulka:
        return ""
    # Pád rozhoduje dřív než výchozí hodnota: `obl` je `kde` obecně,
    # ale v dativu je to `komu_cemu`.
    r = tabulka.get(pad(token)) or tabulka.get("vychozi", "")
    nutne = self.jazyk.role_vyzaduji_predlozku.get(r)
    if nutne and self.predlozka(veta, token) not in nutne:
        return ""
    return r
```

### Čtyři řezy, každý za jednu naměřenou chybu

| řez | co dělá | co bez něj vzniklo |
|---|---|---|
| `role = "" if typ else …` | role mluví jen tam, kde agent není | `Kde se narodil Franz Kafka?` → „ve svých prózách" |
| role se nepustí do širšího pole | rozšíření zahazuje sloveso otázky | `S kým se oženil Hrabal?` → „s Jiřím Kolářem" |
| `PRAZDNE_UPOS` | odpověď musí něco nést | `Komu to řekl?` → „vám" |
| `role_zadaji_jmeno` | na „koho" se neodpovídá slovesem | `Jak se jmenovala matka?` → „přijali" |

První dva jsou tentýž princip: **role je nejslabší důkaz, takže potřebuje
nejsilnější pole.** Typ přežije rozšíření, protože ho ověřil agent — datum
je datum i v širším poli. Role ověřená není.

Mlčení agenta je proto odpověď, ne mezera. Když se ptáme „Kde" a Topos
nenajde místo, znamená to, že v poli žádné není; přebít ho rolí `kde` je
totéž jako vzít první lokál, který se namane.

```python
# core/answers.py — sebrat_roli()
# Role se počítá až nad větami POLE, ne dopředu nad korpusem:
# pole má desítky vět, korpus 25 755.
for i in self.role.role_vety(veta).get(role, ()):
    r = self.role.rozsah(veta, i)     # token + předložka, přívlastek, flat
```

*Naměřeno* na kurátorované sadě, doména `role` (6 otázek):

```
uspěl 5/6 · první 3 · z toho poctivé mlčení 2/2
celkem 40 otázek:  uspěl 82 % · první 61 %   (dřív 34 otázek: 82 % · 59 %)
```

Šest druhů otázek, které dřív nešly vůbec, teď jde — a obě položky, kde
korpus odpověď nemá (`S kým se oženil Hrabal / pes domácí?`), mlčí.

---

## 4c · Zápor a doptání — dvě tiché chyby

Obě vyšly najevo v dialogu, ne v měření. Obě vypadaly jako odpověď.

### Zápor: odpověď byla pravý opak textu

```
Kdo je Božena Němcová?   →   realistkou

  Podle Šaldy proto NENÍ Němcová realistkou, měříme-li realismus tím,
  jak vystihuje hluboké kořeny zla…
```

Zápor v datech nechyběl — spona `není` nese `Polarity=Neg`. Jen se na ni
nikdo nedíval, takže agent orazítkoval `Typ=druh` a odpovídač to podal jako
fakt.

```python
# core/agents/druh.py
@staticmethod
def je_zaporna(veta, t):
    """„není realistkou" je tvrzení o tom, čím ta osoba NENÍ —
    a to je jiný fakt, ne slabší varianta téhož."""
    return any(x.get("head") == t.get("id") and "cop" in x["acts"]
               and "Polarity=Neg" in x["acts"] for x in veta)
```

**Větu nezahazujeme.** Pole je monotónní a informace „realistkou NENÍ" je
plnohodnotná. Dostane vlastní typ `Typ=druh_ne`: na „Kdo je?" se nenabídne,
protože ta otázka se ptá na `Typ=druh`, a přitom v poli zůstane
adresovatelná. Zahodit ji by znamenalo z chybné odpovědi udělat mlčení —
lepší, ale pořád ztráta.

### Doptání: remíza se tiše rozhodla za nás

```python
# bylo: první z nejlepších vyhrává
for klic in self.podle_entity:
    if shoda > skore:
        nejlepsi, skore = klic, shoda      # remízu nikdo neuvidí
```

„Kdo je Novák?" sedí na Karla, Petra i Milana úplně stejně. Vybrat prvního
znamená odpovědět o někom, na koho se nikdo neptal — a nebylo by to poznat.

`entity_pro_jmeno()` proto vrací **všechny** stejně dobré shody a dialog
odpoví jinak:

```
Kdo je Novák?   →   upřesni prosím, koho myslíš: Karel Novák · Petr Novák · Milan Novák
```

**Doptání je vlastní druh tahu, ne varianta mlčení.**

```
mlčení    „o tom korpus nic neví"      chybí data
doptání   „je toho víc, vyber si"      data jsou, chybí otázka
```

Míchat je znamená zahodit informaci, kterou pole má. Starý conBond to měl
v etalonu jako třetí režim `clarify` vedle `answer` a `unsure`.

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
