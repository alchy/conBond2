"""Jazykový profil — česká slova ven z podmínek, do JSON.

CO SEM PATŘÍ a co ne. Jazyků se to v kódu týká na třech různých místech a
jen jedno z nich je tohle:

  1. JAK SE ČTE VĚTA — „je druh", „není", tázací slova, jména měsíců.
     Tady. Je to data, mění se to bez zásahu do kódu a je vidět pohromadě,
     co všechno mluvnice zná.

  2. CO SE VYPÍŠE ČLOVĚKU — „přijato:", „nevím — a mlčení není zápor".
     Sem NE. Je to jiná osa: vstupní mluvnice a výstupní hlášky se mění
     nezávisle a smíchat je znamená překládat log, aby šel číst dotaz.

  3. UPOS, DEPREL, jména skupin vertikál. Sem UŽ VŮBEC. Universal
     Dependencies jsou univerzální a `NOUN` není české slovo; přesunout je
     do souboru `cs.json` by tvrdilo, že jsou.

CO PROFIL NEUMÍ. Nedělá z toho vícejazyčný program. Kromě slov se totiž liší
i PRAVIDLA: „velké písmeno = vlastní jméno" platí v češtině a v němčině je
k ničemu, protože velká jsou tam všechna podstatná jména. Takové pravidlo
je tu proto jako příznak, ne jako seznam — a než někdo napíše `en.json`,
bude potřeba víc než opsat slovíčka.

Skutečný zisk není angličtina, ale tohle: přidat „spadá pod" jde bez sahání
do Pythonu.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

SLOZKA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grammar")
VYCHOZI = "cs"


@dataclass
class Jazyk:
    kod: str = VYCHOZI
    jmeno: str = ""
    spona: tuple = ()
    spona_zapor: tuple = ()
    znacky_podtridy: tuple = ()
    znacky_synonyma: tuple = ()
    tazaci: tuple = ()
    na_zarazeni: tuple = ()
    predlozky: tuple = ()
    velke_pismeno_je_instance: bool = True
    mesice: dict = field(default_factory=dict)
    uvozuje_rok: tuple = ()
    tazaci_na_typ: dict = field(default_factory=dict)
    prazdna: tuple = ()
    deprel_na_roli: dict = field(default_factory=dict)
    tazaci_na_roli: dict = field(default_factory=dict)
    role_podle_prisudku: dict = field(default_factory=dict)
    role_popis: dict = field(default_factory=dict)
    spojky_role: dict = field(default_factory=dict)
    role_vyzaduji_predlozku: dict = field(default_factory=dict)
    role_zadaji_jmeno: tuple = ()
    jmenne_upos: tuple = ()

    # ---- načtení -----------------------------------------------------
    @classmethod
    def cesta(cls, kod: str) -> str:
        return os.path.join(SLOZKA, f"{kod}.json")

    @classmethod
    def nacist(cls, kod: str = VYCHOZI) -> "Jazyk":
        """Profil se veze s kódem, ne s daty: bez něj mluvnice nefunguje
        vůbec, takže to není uživatelský obsah, ale součást knihovny."""
        with open(cls.cesta(kod), encoding="utf-8") as f:
            d = json.load(f)
        return cls.ze_slovniku(d)

    @classmethod
    def ze_slovniku(cls, d: dict) -> "Jazyk":
        # Klíče od podtržítka jsou vysvětlivky pro člověka, ne data.
        znam = {p for p in cls.__dataclass_fields__}
        cist = {k: v for k, v in d.items() if k in znam}
        for k, v in list(cist.items()):
            if isinstance(v, list):
                cist[k] = tuple(v)
        return cls(**cist)

    @classmethod
    def vypsat_dostupne(cls) -> list:
        if not os.path.isdir(SLOZKA):
            return []
        return sorted(j[:-5] for j in os.listdir(SLOZKA) if j.endswith(".json"))

    # ---- dotazy ------------------------------------------------------
    def je_tazaci(self, slovo: str) -> bool:
        return slovo in self.tazaci

    def pta_se_na_zarazeni(self, slovo: str) -> bool:
        return slovo in self.na_zarazeni

    def cislo_mesice(self, slovo: str) -> Optional[int]:
        return self.mesice.get(slovo.lower())

    def uvozuje(self, slovo: str) -> bool:
        return slovo.lower().strip(".") in self.uvozuje_rok

    def na_co_se_pta(self, text: str) -> Optional[str]:
        """Druh místa, kde odpověď leží — nebo None, když to není otázka
        na obsah."""
        for slovo in text.lower().replace("?", " ").split():
            if slovo in self.tazaci_na_typ:
                return self.tazaci_na_typ[slovo]
        return None

    def je_prazdne(self, slovo: str) -> bool:
        return slovo in self.prazdna or slovo in self.tazaci_na_typ
