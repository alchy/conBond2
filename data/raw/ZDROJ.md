# Zdroj textů

Články z české Wikipedie o dvanácti spisovatelích, převzaté z předchozího
projektu conBond (`data/raw/wiki_*.txt`).

Wikipedie je pod licencí **CC BY-SA 4.0**. Texty jsou tu jako baseline korpus
pro měření, ne jako obsah projektu.

Slouží k jedinému: náš původní korpus měl 86 tokenů faktů, což je na měření
zobecnění o dva až tři řády málo. Tenhle má kolem 56 000 slov.

## Doplněk ze starého conBondu (kvůli srovnatelnému měření)

Aby šel projet etalon z předchozího projektu (`data/gold/conbond.json`),
chybělo osm textů. Bez nich by se neměřila schopnost odpovídat, ale to, že
tu ta data nejsou.

Wikipedie, **CC BY-SA 4.0** — díla Karla Čapka, na která se etalon ptá:

    bílá_nemoc.txt · válka_s_mloky.txt · rur.txt

Psané ručně v předchozím projektu, žádný vnější zdroj:

    fyzika_gravitace.txt      Newton a gravitace
    příroda_česká.txt         Šumava, Vltava, Sněžka
    rodina_novákovi.txt       vymyšlená rodina — na vztahy a na shodu jmen
    vztahy_příbuzenské.txt    definice pojmů (tchán, zeť, švagr…)
    poznámky_domácnost.txt    domácí poznámky — pes Rex, chata, auto

Poslední dva jsou jiný druh textu než životopis: definice a poznámky.
Zátěžová zkouška je právě v tom, že v nich nejsou celá jména ani datumy.

## Slovník synonym (`data/lexicon/synonyms.json`)

Převzatý hotový z předchozího projektu — 1016 významových skupin a 549
jednoznačných map na korpusový predikát. Nic se nestahuje: soubor vznikl
tam a runtime je offline.

Zdroj: **slovnik-synonym.cz** (obsah vkládají uživatelé, ověřují editoři;
staženo pro offline použití při přípravě dat).

## Etalon ze starého conBondu (`data/gold/conbond.json`)

95 otázek, tvar `q` / `expect` / `mode` / `kind` / `src`. Vedle `answer`
a `unsure` má i třetí režim `clarify` — otázka, na kterou se má stroj
doptat, protože jméno sedí na víc lidí.
