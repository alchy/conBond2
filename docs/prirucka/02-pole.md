# 02 · Pole — z korpusu šablony

Jádro projektu. Vstup je korpus vět, výstup jsou **šablony**: obálky okolí,
sloučené tam, kde vyšly stejně.

```python
from core import Pole, UlozisteSouboru, Config

pole = Pole(UlozisteSouboru(config=Config.nacist()))
pole.nastavit_polomery(1, 1)      # nastaví se jednou a platí
pole.postavit()
print(pole.fakta.pocet_sablon())
```

---

## 1 · Rozprostření — `Tok`

**Princip.** Věty se poskládají za sebe do jednoho sloupce řádků, ale každá
dostane **r prázdných řádků před sebe a r za sebe**. Okno pak nemá jak
přelézt do sousední věty a nemusí se hlídat okraje — geometrie to udělá
za nás.

```
∅ ∅          ← odsazení (r=2)
Narodil
se
v
Praze
∅ ∅          ← odsazení
Studoval
…
```

**Kontrakt.**

| metoda | role |
|---|---|
| `rozprostrit(vety)` | celý tok i s odsazením |
| `vybrat_tokeny(veta)` | podle zrna: normalizovaně jde interpunkce stranou |
| `odsadit_vetu()` · `vyrobit_prazdne()` | prázdné řádky kolem věty |
| `radek(j)` | řádek, nebo `None` mimo pole |
| `vypsat_stredy()` | řádky, které jsou slovo — možné středy |
| `pocet_radku()` | délka toku |

**Ukázka.** *Ověřeno* — při r=1 nad 25 755 větami: **440 142 řádků**,
z toho **388 632 středů**; zbytek je odsazení. Test hlídá, že při r 0–8
nemíří ani jeden slot mimo pole a ani jeden nepřeleze do sousední věty.

---

## 2 · Okno — `Okno`

**Princip.** Kolem středu `i` leží sloty `i-r … i+r`. Střed sám do vektoru
vstoupí jen tehdy, když se to řekne.

| metoda | role |
|---|---|
| `urcit_sloty(stred)` | seznam `Slot(j, d)` — index řádku a offset |
| `offsety()` | jen offsety, s nulou nebo bez ní |
| `pocet_slotu()` | kolik slotů okno má |
| `zasahuje(d)` | vejde se offset do okna? (paleta podle toho šedne) |

---

## 3 · Zdroj aktivací — `ZdrojZTokenu`

**Princip.** Co token aktivuje. Aktivace jsou v tokenu, ale **pořadí dává
katalog vertikál** — vektor je posloupnost, takže táž sada jinak seřazená
by dala jinou šablonu.

| metoda | role |
|---|---|
| `vypsat_aktivace(token)` | aktivace odfiltrované a v kanonickém pořadí |
| `odfiltrovat_typy(acts)` | vypnutý `Typ=` musí zmizet i z pole, ne jen z vektoru |
| `dopocitat_hrube(acts)` | hrubé vrstvy nad jemnými (viz níž) |
| `seradit_kanonicky(acts)` | pořadí podle katalogu — matice přidává na konec |
| `je_interpunkce(token)` | při normalizovaném zrnu do pole nejde |
| `urcit_tvar(token)` | klíč do slovníku podle zrna |

---

## 4 · Hrubé vrstvy — `Odvozena`

**Princip.** Týž atribut v nižším rozlišení. `NOUN` i `VERB` jsou
`Trida=plny`; `ADP` i `AUX` jsou `Trida=pomocny`. Počítá se při čtení, do
korpusu se nic nedopisuje — je to funkce toho, co tam už je.

```python
ODVOZENE = (
    Odvozena("Trida", "HRUBĚ", "UPOS",  {…}),   # plný / pomocný / jiný
    Odvozena("Uloha", "HRUBĚ", "DEPREL", {…}),  # jádro / rozvoj / jiný
)
```

**Proč to nic nerozbije.** Odvozená hodnota je **funkcí** jemné, takže dvě
slova se stejným UPOS mají i stejnou třídu. Vektor se prodlouží, ale
nerozdělí. *Ověřeno:* 26 624 šablon bez vrstev = 26 624 s vrstvami.
Kdyby vrstva něco rozdělila, není to hrubší pohled na totéž, ale nový
atribut. Test to hlídá.

**K čemu to je.** Smysl dostanou, teprve když sítko pustí hrubou vrstvu
a jemnou ne — viz `SitkoStupnovane`.

---

## 5 · Sítko — pátý šev

**Princip.** Zdroj říká, CO token aktivuje. Sítko říká, jestli se to **na
tomhle místě okna** počítá.

```python
class Sitko(ABC):
    def propustit(self, offset, aktivace): ...
    def je_cinne(self): ...
```

| implementace | co dělá |
|---|---|
| `SitkoVse` | propouští všechno |
| `SitkoStredu(povolene)` | sousedy celé, střed jen ve jmenovaných atributech |
| `SitkoStupnovane(patra)` | rozlišení klesá se vzdáleností |

**Proč vzniklo.** Střed do svého vlastního vektoru nevstupoval, takže
cokoli, co v češtině nese slovo samo, bylo pro jeho šablonu neviditelné:

```
Brno je   město.   -1:PROPN -1:nsubj … +1:NOUN +1:root …   → f02
Brno není město.   -1:PROPN -1:nsubj … +1:NOUN +1:root …   → f02   ← totéž!
```

Pustit dovnitř celý střed to spraví, ale zabije sdílení (57 % → 27 %).
Sítko je střední cesta.

**Kolik to stojí a co koupí.** *Ověřeno*, 34 autorů, r=1:

| střed | šablon | sdíleno | čas | místo |
|---|---:|---:|---:|---:|
| mimo | 53 985 | 59 % | 44 % | 22 % |
| **`NameType`** (výchozí) | 56 644 | 57 % | 48 % | **98 %** |

Dva body sdílení za 76 bodů čistoty místa: „v Praze" a „v bezvědomí" mají
identického souseda a rozlišuje je právě to, co sedí na středu.

> **Past, na kterou je hlídač.** Sítko podstrčené jako šev **nezapne střed
> do okna** — to dělá jen setter `stred_atributy`. Filtrovat střed, který
> není slot, je němé: vypadá to, že se filtruje, a nefiltruje se nic. Přesně
> tak jsem si první sadu měření znehodnotil. `filtruje_stred(sitko)` se
> sítka zeptá aktivací, kterou nemůže znát, a jádro to ohlásí do logu.

---

## 6 · Skládač a slučovač

**Princip.** Vektor je posloupnost `offset:aktivace`. Dvě slova mají tutéž
šablonu, právě když jsou jejich vektory znak po znaku stejné.

```python
class SkladacRetezcem(SkladacVektoru):
    def popsat_slot(self, offset, aktivace):
        if not aktivace:
            return [f"{zapsat_offset(offset)}:∅"]     # prázdný slot
        return [f"{zapsat_offset(offset)}:{a}" for a in aktivace]

    def spocitat_klic(self, vektor):
        return "|".join(vektor)                        # klíč pro slučování
```

`SlucovacShodou.zaradit(vektor, klic)` vrátí id šablony a novou v případě
potřeby založí. Předpona `f` pro fakta, `q` pro dotazy — z id je na první
pohled poznat, ze které strany je.

---

## 7 · Slovník — `Slovnik`

**Princip.** Slovník je **jeden, společný oběma stranám**. Šablony a vazby
má každá strana vlastní. Že je týž tvar ve faktu i v dotazu, samo o sobě
nic nespojuje — je to jen společný prostor tvarů; spojení jde přes šablony.

| metoda | role |
|---|---|
| `naplnit_z_toku(tok, strana)` | plní se z OBOU stran dřív, než se staví šablony |
| `zapsat_radek()` · `zalozit_nebo_najit()` | jeden tvar, jedna položka |
| `zapsat_sadu()` | kolik různých sad aktivací tvar má |
| `zapsat_sablonu(tvar, strana, id)` | zpětný odkaz tvar → šablona |
| `vypsat_tvary_v_obou()` | co je ve faktech i v dotazech |
| `vypsat_nejiste()` | tvary s víc sadami — u skládání se u nich hádá |

---

## 8 · Strana — `Strana`

Jedna strana pole. Tady se to celé potká.

```python
def zaradit_stred(self, i, radek):
    sloty = self.okno.urcit_sloty(i)                    # kam vektor dopadá
    vektor = self.slozit_vektor(sloty)                  # co v těch slotech je
    oznaceni = self.slucovac.zaradit(vektor, self.skladac.spocitat_klic(vektor))
    tvar = self.zdroj.urcit_tvar(radek.token)
    self.pripsat_k_sablone(oznaceni, tvar, i)           # šablona ← tvar
    self.slovo_radku[i] = (self.slovnik.cislo(tvar), oznaceni)
    return oznaceni
```

| metoda | role |
|---|---|
| `postavit()` | celá strana: středy → šablony → vazby |
| `aktivace_slotu(slot)` | prázdný slot i slot mimo pole nepřispějí ničím |
| `sestavit_vazby()` | dvojice (tvar, šablona) → výskyty |
| `spocitat_pomer()` | šablon na střed; blíží-li se 1, nesdílí vzor nikdo |
| `spocitat_prazdne_sloty()` | kolik z okna je odsazení |

**Ukázka.** *Ověřeno*, 25 755 vět, r=1:

```
řádků 440 142 · středů 388 632 · šablon 162 391 · poměr 0.418
nejširší vzor f81: 766 tvarů · -1:CCONJ -1:cc -1:Vyp=proza -1:Trida=pomocny
```

Poměr 0.418 znamená, že na jednu šablonu připadá 2,4 slova — vzory se
sdílejí. Kdyby vyšel blízko 1.0, každé slovo má vlastní vzor a nesbíhá se
ani jedna hrana.

---

## 9 · Fasáda — `Pole`

**Princip.** Poloměr se nevleče každým voláním. Drží ho `Nastaveni`; setter
jen poznamená, že model zestaral, a přepočítá se, až si o výsledek někdo
řekne. Kdyby setter přepočítával sám, nastavení tří věcí za sebou by
průchod spustilo třikrát.

| metoda | role |
|---|---|
| `postavit(vzdy=False)` | celý průchod; když se nic nezměnilo, nedělá nic |
| `vypsat_vertikaly()` | katalog: uložené + hrubé vrstvy, na jednom místě |
| `zapomenout_katalog()` | katalog se změnil zvenku |
| `pripravit_zdroj()` · `pripravit_sitko()` | švy, dají se podstrčit zvenku |
| `fakta` · `dotazy` | strany; sáhnutí na ně staví, pokud je potřeba |
| `nastavit_polomery(f, q)` | dvě r, smí se lišit |
| `ziskat_klic_mapovani()` | `q<rq>f<rf>` — mapování má store na dvojici |

**Proč dvě r.** Dotaz může mít jiné r než fakt, protože se vektory obou
stran **nikdy neporovnávají přímo** — mapování je kotvené na tvarech. Kdyby
se párovaly vektory, musela by být r shodná.
