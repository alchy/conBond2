# Jaké atributy má mít aktivační pole? — podklad k diskusi

## Co stavíme

Text i otázky převádíme na **aktivační pole**: řádek na každé slovo, sloupec
na každý atribut. Buňka svítí, když slovo ten atribut nese.

Pro každé slovo se pak vezme jeho **okolí** v poloměru `r` a z aktivací
sousedů se poskládá vektor s offsety:

```
-1:PROPN  -1:nsubj  -1:Case=Nom  +1:ADJ  +1:amod  +1:Case=Acc
```

Slova se stejným vektorem sdílejí **šablonu** — vzor okolí, ve kterém není
ani jedno konkrétní slovo. Šablona je tedy tvrzení „takhle vypadá kontext".

Totéž běží dvakrát: nad **fakty** (text) a nad **dotazy** (otázky). Slovník
tvarů je společný, ale šablony i vazby má každá strana vlastní. Odpovídání
na otázku pak není hledání v textu, ale **spárování šablony otázky se
šablonou faktu**.

Cíl je zobecnění: chceme, aby otázka, kterou stroj nikdy neviděl, spadla do
šablony, kterou už zná.

## Jak jsou atributy uspořádané

Sloupce máme rozdělené do skupin podle původu. První tři dává UDPipe
(model `cs_all-ud-2.17`), poslední tři jsme přidali sami.

| skupina | sloupců | nese tokenů | původ |
|---|---:|---:|---|
| UPOS | 17 | 411 (100 %) | UDPipe — slovní druh |
| DEPREL | 43 | 411 (100 %) | UDPipe — závislostní vztah k řídícímu slovu |
| FEATS | 90 | 327 (80 %) | UDPipe — morfologické rysy |
| TYP | 6 | 112 (27 %) | ručně — významový typ |
| LEM | 25 | 109 (27 %) | ručně — lemma u zavřených tříd |
| PTÁ | 17 | 52 (13 %) | ručně — tvar tázacího slova |
| **celkem** | **198** | | |

Korpus je zatím malý a slouží jako sonda: **8 vět faktů (86 tokenů)** a
**60 otázek (325 tokenů)**. Token nese průměrně **6,3 aktivace**.

### UPOS (17)
```
NOUN PUNCT VERB ADP ADJ PRON DET CCONJ PROPN AUX ADV SCONJ NUM PART SYM X INTJ
```

### DEPREL (43)
```
punct case conj nsubj root nmod amod obl cc obj obl:arg det advmod mark cop
expl:pv advmod:emph aux advcl ccomp acl:relcl flat nummod appos xcomp aux:pass
parataxis nsubj:pass dep advcl:pred vocative nummod:gov acl orphan compound
fixed csubj expl:pass discourse det:numgov csubj:pass iobj det:nummod
```

### FEATS (90 hodnot ve 29 rysech)

| rys | hodnot | hodnoty |
|---|---:|---|
| PronType | 9 | Prs, Dem, Int,Rel, Tot, Ind, Neg, Rel, Emp, Dem,Ind |
| NameType | 9 | Giv, Geo, Nat, Oth, Giv,Nat, Geo,Giv, Giv,Oth, Geo,Oth, Geo,Giv,Oth |
| Case | 7 | Nom, Acc, Gen, Loc, Ins, Dat, Voc |
| Gender | 6 | Masc, Fem, Neut, Masc,Neut, Fem,Neut, Fem,Masc |
| VerbForm | 5 | Fin, Part, Inf, Vnoun, Conv |
| Number | 4 | Sing, Plur, Plur,Sing, Dual |
| NumType | 4 | Card, Ord, Mult, Sets |
| ExtPos | 4 | ADP, CCONJ, SCONJ, ADV |
| Aspect, Tense, Person, Mood, AdpType, Degree, NumForm, Gender[psor] | 3 každý | |
| Polarity, Animacy, Voice, Number[psor], PrepCase | 2 každý | |
| Variant, Reflex, Poss, Abbr, Foreign, Hyph, ConjType, Style | 1 každý | Short, Yes, Yes, Yes, Yes, Yes, Oper, Coll |

### Naše tři vrstvy

```
TYP (6)   Typ=osoba  Typ=zivocich  Typ=vec  Typ=misto  Typ=cas  Typ=dej
LEM (25)  Lem=a Lem=být Lem=co Lem=do Lem=jaký Lem=jeho Lem=k Lem=kdo
          Lem=kolik Lem=který Lem=mezi Lem=na Lem=nebo Lem=než Lem=o Lem=on
          Lem=protože Lem=s Lem=se Lem=svůj Lem=ten Lem=tento Lem=u Lem=v Lem=čí
PTÁ (17)  Ptá=kdo Ptá=co Ptá=koho Ptá=komu Ptá=kým Ptá=čí Ptá=jak Ptá=kdy
          Ptá=kde Ptá=kam Ptá=proč Ptá=který Ptá=kterou Ptá=kterém
          Ptá=jaký Ptá=jaké Ptá=jakou
```

**Proč LEM jen u zavřených tříd:** u předložek a spojek je lemma mluvnice,
ne obsah. Bez něj jsou „do lesa" a „u dveří" v poli nerozlišitelné.

**Proč PTÁ:** UDPipe dává `jak`, `kdy`, `kam`, `kde` a `proč` **jeden a týž
podpis** `ADV advmod PronType=Int,Rel`. Pět sémanticky nejvzdálenějších
otázek — způsob, čas, směr, místo, důvod — by spadlo do jedné šablony.
Lemma nestačí: `co` a `koho` se ptají na jinou věc, ale lemma mají totéž.

## Ukázka

Věta „Karel má velkého psa, který se jmenuje Alfons." jako řádky pole:

```
Karel      PROPN nsubj Animacy=Anim Case=Nom Gender=Masc NameType=Giv
           Number=Sing Typ=osoba
má         VERB root Aspect=Imp Mood=Ind Number=Sing Person=3 Polarity=Pos
           Tense=Pres VerbForm=Fin Voice=Act
velkého    ADJ amod Animacy=Anim Case=Acc Degree=Pos Gender=Masc Number=Sing
           Polarity=Pos
psa        NOUN obj Animacy=Anim Case=Acc Gender=Masc Number=Sing Typ=zivocich
```

Šablony při `r=1` (střed do vektoru nevstupuje):

```
t01   sdílí: alfons, karel
      -1:∅ +1:VERB +1:root +1:Number=Sing +1:Polarity=Pos +1:VerbForm=Fin
      +1:Aspect=Imp +1:Voice=Act +1:Tense=Pres +1:Person=3 +1:Mood=Ind

t02   sdílí: má
      -1:PROPN -1:nsubj -1:Number=Sing -1:Case=Nom -1:Gender=Masc
      -1:Animacy=Anim -1:NameType=Giv -1:Typ=osoba
      +1:ADJ +1:amod +1:Number=Sing +1:Case=Acc +1:Gender=Masc
      +1:Polarity=Pos +1:Animacy=Anim +1:Degree=Pos
```

`∅` je prázdný slot: každá věta je odsazená `r` prázdnými řádky, takže okno
nemá jak přelézt do sousední věty.

## Problém, kvůli kterému se ptáme

**Zobecnění nám umírá.** Poměr počtu šablon k počtu slov by měl být výrazně
pod jednou — jedna šablona má popisovat víc slov. Měříme tohle:

| r | fakta (šablon/slov) | poměr | dotazy (šablon/slov) | poměr |
|---:|---|---:|---|---:|
| 0 | 51 / 75 | 0,68 | 87 / 260 | 0,33 |
| 1 | 71 / 75 | 0,95 | 161 / 260 | 0,62 |
| 2 | 75 / 75 | **1,00** | 226 / 260 | 0,87 |
| 3 | 75 / 75 | **1,00** | 251 / 260 | 0,97 |
| 8 | 75 / 75 | **1,00** | 251 / 260 | 0,97 |

Od `r=2` má **každé slovo faktů vlastní šablonu**. Nic se nesdílí, žádné dvě
místa v textu nejsou pro stroj podobná. Vektor je při 6,3 aktivacích na token
a poloměru 2 dlouhý kolem 25 položek a musí se shodovat **přesně** — a to se
při takové jemnosti nestane skoro nikdy.

Máme tedy podezření, že **atributů je moc, nebo jsou to nesprávné atributy**.
Zvlášť podezřelé nám připadá:

* **FEATS táhne vektor dolů nejvíc.** Rysy jako `Gender`, `Number`, `Case`
  jsou u češtiny všudypřítomné a rozlišují i tam, kde nechceme.
* **Rysy, které nejspíš nic nepřinášejí:** `NameType` (9 hodnot!), `Style=Coll`,
  `Hyph`, `Foreign`, `Abbr`, `Variant=Short`, `NumForm`.
* **Naše vrstvy jsou řídké** — TYP a LEM po 27 %, PTÁ 13 %. Nese je menšina
  tokenů, takže na většině míst pole nepomáhají.
* **20 ze 104 tvarů má víc různých sad aktivací**, takže tentýž tvar se
  v poli chová pokaždé jinak.

## Na co se ptáme

1. **Které atributy do pole patří a které ne?** Máme brát všechny FEATS, nebo
   jen podmnožinu? Podle čeho ji vybrat?

2. **Nemá se místo plochého seznamu zavést hierarchie nebo váha?** Například
   aby `Case=Nom` a `Case=Acc` byly „blíž k sobě" než `Case=Nom` a `VERB`, a
   šablony se slučovaly podle podobnosti místo přesné shody.

3. **Jaké sémantické vrstvy nám chybí?** Máme jen `Typ=` se šesti hodnotami
   (osoba, živočich, věc, místo, čas, děj). Co by mělo přibýt, aby se otázka
   a fakt potkaly na významu, a ne na morfologii?

4. **Má se pro fakta a pro otázky brát jiná sada atributů?** Otázka a fakt
   jsou různé žánry; u otázky nás nejspíš zajímá tázací tvar a slovesná
   valence, u faktu spíš sémantické role.

5. **Není chyba, že vektor je posloupnost řetězců porovnávaná na přesnou
   shodu?** Nabízí se řídký číselný vektor a podobnost, ale ztratili bychom
   čitelnost, na které nám záleží — pole má jít přečíst okem.

Architektura je na výměnu připravená: máme oddělené švy pro zdroj aktivací,
pro způsob skládání vektoru a pro slučování do šablon, takže odpovědi typu
„jinak vážit" nebo „slučovat podle podobnosti" jdou zkusit bez přepisu jádra.

Zajímá nás názor jak na výběr atributů, tak na to, jestli je celý přístup
„přesná shoda dlouhého vektoru" udržitelný, nebo se láme právě tady.
