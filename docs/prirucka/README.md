# Příručka conBond2

Psáno pro vývojáře, který o projektu neví nic. Ke každému mechanismu je
**princip** (nezávisle na kódu), **kontrakt** (co bere, co vrací, co mění na
disku) a **ukázka** ze skutečného korpusu.

1. [Mapa — co kudy teče](00-mapa.md) · diagramy všech workflow
2. [Extrakce](01-extrakce.md) · syrový text → korpus
3. [Pole](02-pole.md) · korpus → vektory → šablony
4. [Dotazování](03-dotazovani.md) · otázka → aktivace → kandidáti
5. [Tvorba otázek](04-otazky.md) · zlatá sada, etalon, měření
6. [Zaměření tématu](05-tema.md) · výřez, vzory, domény, zdraví
7. [Dialog a znalost](06-dialog.md) · věta → tvrzení → odvození
8. [Rejstřík metod](07-metody.md) · všech 312 metod a jejich role

## Rychlý start

```bash
./udpipe.sh                          # rozbor vět, port 9010
python3 -m server start              # API a stránka, port 9000
python3 -m core.health               # kontrola dat

python3 scripts/baseline.py vse      # data/raw/*.txt → korpus
python3 scripts/otazky.py generuj    # korpus → zlatá sada
python3 scripts/odpovedi.py          # měření na generované sadě
python3 scripts/etalon.py            # měření na kurátorované sadě
python3 scripts/domeny.py            # přenos vzorů mezi tématy
python3 test/core.py                 # testy jádra
```

## Jednou větou

Text se rozprostře do sloupce řádků, kolem každého slova se z jeho okolí
složí vektor, stejné vektory splynou v **šablonu**. Šablona neříká, co to
slovo je — říká, **jaké místo ve větě** to je. Odpovídání pak není hledání
v textu, ale rozsvícení toho místa.
