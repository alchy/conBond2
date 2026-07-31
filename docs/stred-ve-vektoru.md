# Střed ve vlastním vektoru

Měřeno 31. 7. 2026. Vzniklo z pokusu, jestli pole pozná druh tvrzení samo,
bez zvláštní mluvnice (`scripts/experiment_tvrzeni.py`).

## Co se ukázalo

Střed do svého vektoru nevstupoval. Vektor byl obálkou okolí — a to je pro
fakta správně. Jenže **cokoli, co v češtině nese slovo samo, je pro jeho
vlastní šablonu neviditelné.**

Se středem mimo, r=1, kotva na sponě:

```
Brno je   město.   -1:PROPN -1:nsubj -1:Number=Sing … +1:NOUN +1:root …   → t02
Brno není město.   -1:PROPN -1:nsubj -1:Number=Sing … +1:NOUN +1:root …   → t02
```

Znak po znaku totéž. Věty se liší jen tím slovem, které je středem, takže po
složení obálky mezi nimi nezbyl žádný rozdíl. V měření to byla šablona `t46`
se šesti členy, `{'instance': 3, 'zapor': 3}`.

Se středem uvnitř se liší v jediném slotu:

```
Brno je   město.   … 0:AUX 0:cop 0:Polarity=Pos …   → t02
Brno není město.   … 0:AUX 0:cop 0:Polarity=Neg …   → t05
```

UDPipe tu informaci dodával celou dobu. Netýká se to jen záporu — stejně
neviditelný byl čas, osoba a způsob, protože je čeština taky věší na sloveso.

## Proč nešlo prostě pustit celý střed dovnitř

Spisovatelský korpus, 52 150 slov, r=1:

| střed | šablon | poměr | slov ve sdílených vzorech |
|---|---:|---:|---:|
| mimo | 26 624 | 0.511 | 57 % |
| celý uvnitř | 37 998 | 0.729 | 27 % |

Šablona přestala být obálkou *okolí* a stala se popisem *toho slova*. Vzor
`-1:CCONJ -1:cc +1:∅` („…a X." na konci věty) sdílelo 189 různých slov; se
středem uvnitř se týchž 195 výskytů rozpadlo do 92 šablon, roztříděných podle
pádu, čísla a rodu středu:

```
t444    13×   filosofie, kritiky, lásky, reality      NOUN Gen Sing Fem
t5371    8×   dramatik, esejista, pedagog, právník    NOUN Nom Sing Masc
t2837    6×   badatelů, lidí, maloměšťáků, poutníků   NOUN Gen Plur Masc
t4761    6×   1818, 1833, 1920, 1921, 1957            NUM
```

Tím zmizí to, kvůli čemu pole existuje: že „dramatik" a „filosofie" stojí na
stejném místě věty, a tedy odpovídají na stejnou otázku.

## Řešení: sítko (`core/sieve.py`)

Střed do okna vpustit, ale propustit z něj jen jmenované atributy. Dvě páčky
místo jedné:

* `stred_uvnitr` — je offset 0 vůbec slot?
* `stred_atributy` — co z něj projde? Prázdné = všechno.

Jméno se píše jako přesná aktivace (`Polarity=Neg`), jako atribut
(`Polarity`) nebo jako skupina vertikál (`FEATS`); stačí, když sedí jedna
úroveň. Nastavení neprázdných `stred_atributy` zapne `stred_uvnitr` samo —
filtrovat střed, který v okně není, nedává smysl.

Je to pátý šev vedle `ZdrojAktivaci`, `Uloziste`, `SkladacVektoru` a
`Slucovac`. Zdroj říká, CO token aktivuje; sítko říká, jestli se to na tomhle
místě okna počítá.

## Kolik to stojí a co to koupí

Fakta, tentýž korpus:

| nastavení středu | šablon | poměr | sdíleno |
|---|---:|---:|---:|
| mimo | 26 624 | 0.511 | 57 % |
| celý uvnitř | 37 998 | 0.729 | 27 % |
| **uvnitř: Polarity** | 28 578 | 0.548 | **52 %** |
| uvnitř: Polarity, Tense | 29 147 | 0.559 | 51 % |
| uvnitř: Polarity, Tense, Mood, Person | 29 465 | 0.565 | 50 % |

Tvrzení, 41 vět čtyř druhů, kotva na sponě:

| střed | šablon (r=1) | čistota | rozlišené druhy |
|---|---:|---:|---|
| mimo | 16 | 71 % | 3/4 — zápor splývá s instancí |
| celý uvnitř | 23 | 93 % | 4/4 |
| **uvnitř: Polarity** | 23 | **93 %** | **4/4** |

Samotné `Polarity` dělá na tvrzeních celou práci — výsledek je totožný
s celým středem, včetně počtu šablon — a na faktech stojí 5 bodů sdílení
místo 30.

## Přílepek: totéž přes vzdálenost

Sítko dostává offset, ne jen aktivace, takže se stejnou pákou dá řídit i to,
kolik se toho vidí **do dálky**. `SitkoStupnovane`: blízko podrobně, daleko
hrubě.

Změřeno na témž korpusu, střed = `Polarity` ve všech řádcích:

| na dálku vidět | délka vektoru | šablon | poměr | sdíleno |
|---|---:|---:|---:|---:|
| r=1, dál nic | 14 | 28 578 | 0.548 | 52 % |
| r=2, na ±2 vše | 26 | 46 484 | 0.891 | 10 % |
| r=2, na ±2 jen UPOS (17 hodnot) | 16 | 40 980 | 0.786 | 24 % |
| **r=2, na ±2 hrubá třída (3 hodnoty)** | 16 | 34 820 | 0.668 | **38 %** |
| r=3, na ±2 a dál hrubá třída | 18 | 40 345 | 0.774 | 25 % |

Dohlédnout o slovo dál stojí 42 bodů sdílení plným pohledem a 14 bodů hrubým.
Je to týž zákon, který vyšel u výběru atributů — cena ≈ pokrytí × mohutnost —,
jen zapsaný přes vzdálenost.

Ta „hrubá třída" je pomocný atribut o třech hodnotách (plnovýznamové /
pomocné / ostatní) odvozený z UPOS. V měření se přidával zvenku přes vlastní
`ZdrojAktivaci`; jako vertikála v katalogu zatím není.

Dvě mezní hodnoty stojí za zapamatování: patro, které nepustí **nic**, splyne
s prázdným slotem, takže je to totéž jako menší poloměr — ověřeno, `r=3` s
prázdným ±3 dalo znak po znaku tytéž počty jako `r=2`. A klíč `None` (zbytek)
se úmyslně **netýká offsetu 0**: kdo píše útlum podle vzdálenosti, na střed
nemyslí a tiché oříznutí středu by bylo překvapení.

### Past, na kterou je hlídač

Sítko podstrčené jako šev **nezapne střed do okna** — to dělá jen setter
`stred_atributy`. Filtrovat střed, který není slot, znamená filtrovat vzduch,
a je to němé: vypadá to, že se filtruje, a nefiltruje se nic. Přesně tak jsem
si první sadu měření znehodnotil.

`filtruje_stred(sitko)` se sítka zeptá aktivací, kterou nemůže znát; když ji
zahodí a střed přitom v okně není, jádro to při stavbě ohlásí do logu.

## Co zůstává otevřené

* **Frontend.** API bere `?stred_atr=Polarity,Tense`; v prohlížeči zatím není
  ovládání. Rozumné místo je list Vertikály — každý sloupec by dostal příznak
  „smí na střed" —, ale to je rozhodnutí o rozvržení, ne o jádru.
* **Kolik toho unese volnější formulace.** Těch 93 % je na 41 uměle
  vyrobených tvrzeních. Ukazuje to, že rozdíl v datech JE a pole ho umí
  zachytit; neukazuje, že to vydrží mimo pokusnou sadu.
* **Zda má být nastavení per korpus.** Zatím platí pro obě strany společně.
  Se sítkem to netlačí tak jako předtím, protože už se nemusí volit mezi
  dvěma krajnostmi.
