# Hrubé vrstvy — týž atribut v nižším rozlišení

Větev `attribute-granularity`. Navazuje na [sítko](stred-ve-vektoru.md).

## Odkud to přišlo

Sítko umí říct, co se na kterém offsetu počítá, a měření ukázalo, že cena
slotu závisí na **mohutnosti** toho, co se v něm vidí. Dohlédnout o slovo dál
stálo 42 bodů sdílení plným pohledem a 33 bodů přes UPOS. Chtělo to hrubší
hodnotu — jenže UPOS je nejhrubší, co UDPipe dodá, a sedmnáct hodnot je pořád
moc.

## Co to je

Deklarovaný převod z jemné hodnoty na hrubou (`core/derived.py`):

| vrstva | z čeho | hodnoty |
|---|---|---|
| `Trida` | UPOS | `plny` · `pomocny` · `jiny` |
| `Uloha` | DEPREL | `jadro` · `rozvoj` · `jiny` |

`NOUN` i `VERB` jsou `Trida=plny`; `ADP` i `AUX` jsou `Trida=pomocny`.
Počítá se to při čtení. Do korpusu se nic nedopisuje, protože je to funkce
toho, co v něm už je.

## Proč se tím nic nerozbije

Odvozená hodnota je **funkcí** jemné, takže dvě slova se stejným UPOS mají
i stejnou třídu. Vektor se prodlouží, ale nerozdělí: šablony, které splývaly,
splývají dál. Ověřeno na spisovatelském korpusu — počty sedí na kus:

| | bez vrstev | s vrstvami |
|---|---:|---:|
| r=1 | 26 624 šablon, délka 12 | 26 624 šablon, délka 15 |
| r=2 | 46 301 šablon, délka 21 | 46 301 šablon, délka 29 |

Kdyby vrstva něco rozdělila, není to hrubší pohled na totéž, ale nový
atribut — a ten by měl stát to, co každý jiný. Test to hlídá.

## K čemu to je

Smysl dostanou teprve tehdy, když sítko pustí hrubou vrstvu a jemnou ne.
Spisovatelský korpus, r=2, na `±2` vidět jen:

| na ±2 vidět | délka | šablon | sdíleno |
|---|---:|---:|---:|
| vše | 29 | 46 301 | 10 % |
| UPOS + DEPREL | 18 | 43 754 | 17 % |
| UPOS (17 hodnot) | 17 | 40 192 | 26 % |
| Trida + Uloha | 19 | 38 516 | 30 % |
| Uloha (3 hodnoty) | 17 | 35 787 | 37 % |
| **Trida (3 hodnoty)** | 17 | **33 264** | **42 %** |
| *(r=1, dál nic)* | 15 | 26 624 | 57 % |

`Trida` sama je z toho nejlepší a obě dohromady jsou horší než každá zvlášť —
dvě hrubé vrstvy jsou pořád dva sloty navíc.

## Kudy to teče

Katalog se skládá ve fasádě, ne v úložišti: `Pole.vypsat_vertikaly()` =
uložené + hrubé. Úložiště má vracet, co je uložené, a hrubé vrstvy uložené
nejsou. Zdroj, sítko i export musejí vidět **týž** katalog, jinak by se
rozešlo kanonické pořadí a s ním všechny šablony.

Prohlížeč dostane katalog i věty s vrstvami — musí je umět vykreslit.
Zpátky se ale neukládají (`bez_odvozenych`, `ocistit_korpus`), protože jinak
by se zapekly do dat a při změně tabulky by v nich zůstala stará čísla.
Ověřeno třemi koly tam a zpět: 204 sloupců pořád, na disku 198 a z toho
0 hrubých.

## Co zůstává otevřené

* **Jestli ten dosah něco koupí.** Zatím víme, co reach stojí, ne co za něj
  je. Sdílení je jedna osa; druhou musí dát úloha — buď měření zásahu pole,
  nebo rozlišení druhů tvrzení při větším okně.
* **Další vrstvy.** `Pad` z Case (přímý / nepřímý), `Cislo` z Number. Přidat
  jde jedním řádkem do `ODVOZENE`, ale bez měření to je jen delší vektor.
* **Prohlížeč.** Hrubé sloupce v mřížce vidět jsou, ovládání sítka ne — pořád
  platí, že rozumné místo je list Vertikály.
