# 06 · Dialog a znalost — znalost se zadává větou

Ne porozumění volnému textu. Pár tvarů, které se píšou skoro česky, ale
čtou se jednoznačně.

```
román je druh díla              podtřída    ⊂
Krakatit je román               instance    ∈
kompatibilita = slučitelnost    synonymum   =
Krakatit není báseň             zápor       ≠
? Krakatit dílo                 dotaz na vztah   → ano / ne / nevím
?? Krakatit                     rodokmen — čím vším to je
Kde se narodil Hrabal?          dotaz na OBSAH   → kandidáti z pole
```

---

## 1 · Čtyři druhy, protože splést je znamená nesmysl

Všechny čtyři jsou v češtině „X je Y", ale chovají se úplně jinak:

| druh | chování |
|---|---|
| podtřída | expanduje se nahoru — otázka na dílo trefí román |
| instance | neexpanduje, je to konkrétní věc, ne třída |
| synonymum | oba pojmy splynou v jeden uzel |
| zápor | drží se zvlášť, čte se až při odpovídání |

Kdyby se instance četla jako podtřída, z „Karel Čapek je člověk" a „člověk
je savec" vyjde, že Čapek je DRUH savce — a začne se chovat jako třída.

**Zápor je jiný druh objektu.** Pole je monotónní: aktivace říká, co JE.
Že něco NENÍ, v něm vyjádřit nejde a chybějící aktivace znamená „nevíme",
ne „ne". Proto se zápory drží stranou a čtou se až při odpovídání.

---

## 2 · Mluvnice — `Mluvnice.rozeber()`

**Princip.** Věta → `Tvrzeni` | `Dotaz` | `Nejasnost` | `None`.
**Otázka se testuje PRVNÍ.**

```python
syrova = sceli_zkratky(veta.strip())
cista = syrova.rstrip(".!?")
if syrova.endswith("?") or self.jazyk.je_tazaci(self._prvni_slovo(cista)):
    return self._dotaz(cista, veta)          # ← dřív než cokoli jiného
```

**Proč.** „Co je Šmoula?" má tvar „X je Y" a bez tohohle se zapsala jako
fakt, že *co* je šmoula — s velkým písmenem rovnou jako instance, s malým
přes nejasnost, kde se navíc nabídla volba DRUH/KONKRÉTNÍ, která tam neměla
co dělat.

| metoda | role |
|---|---|
| `rozeber(veta)` | rozcestník; otázka první, pak synonymum, zápor, podtřída, spona |
| `_dotaz(cista, veta)` | „Co je X?" → zařazení · „Je X Y?" → ano/ne |
| `_najit(veta, znacky)` | první značka z profilu, která ve větě je |
| `_obsahuje(veta, znacka)` | hledá v ODSAZENÉM řetězci — chytí i kraj věty |
| `_rozdel(veta, znacka)` | dělí v TÉMŽ odsazeném řetězci |
| `_pojem(kus)` | lemma jako klíč |
| `_ocistit(kus)` | povrchový tvar k zobrazení |

> **Pětistovka z jednoho neodsazení.** Značka se hledala v odsazeném
> řetězci, ale dělila v neodsazeném. Věta začínající značkou —
> `Je Šmoula skřítek?` — test prošla a na dělení spadla `ValueError` ven
> jako HTTP 500.

**Lemma je klíč, napsaný tvar se zobrazuje.**

```python
@dataclass
class Tvrzeni:
    levy: str          # lemma — podle něj se pojmy potkávají
    levy_tvar: str     # co člověk napsal — jen k zobrazení
```

Víceslovný pojem se lemmatizuje po slovech, takže „pohádková bytost" vyjde
jako „pohádkový bytost". Jako klíč je to v pořádku a shoda funguje, ale
ukazovat se to nemá.

**Když si mluvnice není jistá, zeptá se.** „pes je savec" může být podtřída
i instance a hádat je horší — špatná hrana se šíří expanzí dál.

---

## 3 · Znalost — `Znalost`

| metoda | role |
|---|---|
| `prijmi(t)` | `None` při přijetí, jinak důvod odmítnutí (kruh, rozpor) |
| `zastupce(pojem)` | synonyma splývají v jeden uzel; tohle je jeho jméno |
| `predci(pojem)` | všechno, čím pojem tranzitivně JE — **tohle je ta expanze** |
| `potomci(pojem)` | opačný směr: otázka smí zobecňovat dolů k instancím |
| `je(co, cim)` | `True` / `False` / **`None`** |
| `zna(pojem)` | padlo o něm někdy slovo? (k rozřezání otázky) |
| `tvar(pojem)` | jak se to napsalo, když o tom poprvé padlo slovo |
| `naplnit_ze_svazu(cesta)` | podklad z Wikidat, hrany dostanou zdroj |
| `vycistit()` | zpět k holému podkladu |

**Tři hodnoty, ne dvě.** `None` znamená poctivě „nevím". Chybějící hrana
není zápor — pole je monotónní a mlčení neznamená popření.

> **Proč `vycistit()` nestačí smazat seznam tvrzení.** Hrany z nich už leží
> v `nadrazene` promíchané s hranami ze svazu a rozeznat je tam po sobě
> nejde. Vyklidí se všechno a svaz se natáhne znovu — proto si `Znalost`
> pamatuje, odkud přišel.

---

## 4 · Rozhovor — `Rozhovor`

**Princip.** Věta dovnitř, záznam ven. Prohlížeč nerozhoduje o ničem.

```python
def poslat(self, text):
    if self.nejasne is not None:
        return …                      # čeká na rozhodnutí, další větu nepřijme
    if text.startswith("??"): return self.rodokmen(text[2:])
    if text.startswith("?"):  return self.odpovedet(text[1:])
    if self.odpovidac and self.odpovidac.je_na_obsah(text):
        return self.z_pole(text)      # ← otázka na OBSAH jde do pole
    return self.prijmout(text)        # ← tvrzení jde do znalosti
```

**Dva druhy otázek.** „Je Krakatit dílo?" se ptá na VZTAH a odpovídá
znalost. „Kde pracoval Hrabal?" se ptá na OBSAH a odpovídá pole — vrátí
**kandidáty**, ne jednu odpověď, protože šablona je abstrakce, která má
kandidáty matchnout; vybrat z nich je jiná úloha.

| metoda | role |
|---|---|
| `poslat(text)` | jeden řádek od člověka; rozcestník |
| `z_pole(text)` | odpověď z korpusu i s aktivací |
| `prijmout(text)` | tvrzení do znalosti, nebo nejasnost |
| `rozhodnout(druh)` | odpověď na nejasnost |
| `preskocit()` | nejasnost zahodit |
| `odpovedet_pojmy(co, cim, text)` | ano / ne / nevím |
| `zaradit(pojem, text)` | čím vším pojem je |
| `rozdelit(dotaz)` | kde v „Je Šmoula pohádková bytost?" končí první pojem |
| `vypsat_stav()` | `{historie, znalost, nalez, ceka}` pro prohlížeč |
| `zapomenout()` | zpět k holému svazu |

**Nejasnost rozhovor zastaví.** Do rozhodnutí se další věta nepřijme — jinak
by se rozdělaná hrana ztratila.

**Rozdělení víceslovného pojmu.** „Je Šmoula pohádková bytost?" nejde
rozdělit podle posledního slova (vyjde „Šmoula pohádková" / „bytost").
Mluvnice to rozhodnout nemůže, obě strany smějí být víceslovné — řez proto
vybírá `Rozhovor` podle toho, po kterém obě strany něco znamenají.

---

## 5 · Celá smyčka — `scripts/ukazka.py`

Systém nezná nic, dostane pár označených vět a pak neoznačené. Druh nové
věty se nehádá z klíčových slov — pozná se podle toho, se kterým semínkem
sdílí šablonu v poli.

```
python3 scripts/ukazka.py
```

*Ověřeno:*

```
semínek 7 → šablon s jednoznačným druhem: 5 z 5
    f02 = instance   f05 = zapor   f07/f10 = podtrida   f13 = synonymum

„Máj je epos."         →  f02 = instance   máj ∈ epos
„Máj není román."      →  f05 = zapor      máj ≠ román
„Bajka je druh díla."  →  f17: tenhle tvar neznám, ptám se

je krakatit dílo?  → ano      (expanzí: román ⊂ dílo)
je máj dílo?       → ano      (přes větu, kterou pole zařadilo samo)
je máj román?      → NE       (zapsaný zápor)
je máj film?       → nevím    (o filmu nepadlo ani slovo)
```

**Tři různé odpovědi ze tří různých důvodů.** Skript běží třikrát a ukazuje
i to, co se stane bez sítka: kladná a záporná věta se sejdou na jedné
šabloně a buď je sporná (systém ztratí obojí), nebo — když nikdo nezasel
záporný příklad — se tváří jistě a je vedle: z „Máj není román" vyjde, že
Máj román JE. Druhý případ je horší, protože není poznat.
