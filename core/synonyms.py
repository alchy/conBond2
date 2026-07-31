"""Slovník synonym — můstek přes lexikální mezeru.

PROČ. Pole se skládá z TVARŮ. Otázka „Co hlásal Ježíš?" se s větou „Ježíš
kázal v synagogách" nepotká, ačkoli se ptá přesně na ni: „hlásat" a „kázat"
jsou dvě slova pro touž věc a rejstřík o tom neví.

Je to táž mezera, jaká vyšla najevo u rolí — „S kým se oženil Hrabal?"
nenašlo nic, protože korpus mluví o svatbě jinými slovy. Zúžení pole tam
nepomůže; chybí DOSAH.

CO SE PŘEBÍRÁ. Hotový slovník z předchozího conBondu
(`data/lexicon/synonyms.json`): významové skupiny stažené při přípravě dat
ze slovnik-synonym.cz. Runtime nic nestahuje.

    synonyma    kázat → [[poučovat, kárat], [hlásat, zvěstovat]]
    pred_fold   hlásat → kázat        jen JEDNOZNAČNÉ mapy

DVA STUPNĚ, NE JEDEN. `pred_fold` je bezpečný: mapuje jen tam, kde slovo má
v korpusu jediný protějšek. Významové skupiny bezpečné nejsou — „kázat"
znamená hlásat i kárat a vzít obojí znamená rozšířit pole o věty, které
s otázkou nesouvisí. Proto se skupiny nabízejí zvlášť a volající si
rozhodne, jestli je pustí.

LEMMA JE PODMÍNKA, A MUSÍ BÝT Z ROZBORU. Slovník je lemmatický, rejstřík pole
tvarový. Na straně korpusu drží můstek `lemma` uložené mimo `acts` — do
vektoru se nedostane, ale dá se podle něj hledat.

Na straně OTÁZKY lemma není, protože otázka je řetězec. První pokus ho
odhadoval ze společného prefixu se slovníkem, a je to slepá ulička: čeština
mění kmenovou samohlásku, takže „kázal"/„kázat" mají společná čtyři písmena
a „zemřel"/„zemřít" tři. Práh, který by je spojil, spojí i „zemřel" se
„zemí". Lemma proto musí dodat rozbor — `Odpovidac` bere lemmatizátor jako
volitelný šev a bez něj se synonyma prostě nepoužijí.
"""

import json
import os
from typing import Iterable, Optional


class Synonyma:
    """Lemma → jiná lemmata, která znamenají totéž."""

    def __init__(self, fold: Optional[dict] = None, skupiny: Optional[dict] = None,
                 zdroj: str = ""):
        self.fold = fold or {}
        self.skupiny = skupiny or {}
        self.zdroj = zdroj
        self.klice = sorted(set(self.fold) | set(self.skupiny))

    @classmethod
    def nacist(cls, cesta: str) -> "Synonyma":
        """Chybějící soubor není chyba — bez slovníku se jen nic nepřeloží.
        Synonyma jsou vylepšení dosahu, ne podmínka běhu."""
        if not os.path.exists(cesta):
            return cls()
        with open(cesta, encoding="utf-8") as f:
            d = json.load(f)
        return cls(fold=d.get("pred_fold") or {}, skupiny=d.get("synonyma") or {},
                   zdroj=d.get("zdroj", ""))

    def __bool__(self) -> bool:
        return bool(self.fold or self.skupiny)

    def slozit(self, lemma: str) -> str:
        """Slovo otázky → jeho korpusový protějšek, nebo ono samo.

        Jednoznačná mapa: `pred_fold` obsahuje jen ta slova, která mají
        v korpusu jediný protějšek. Kde je významů víc, tam se nemapuje —
        raději se nenajde nic než něco z jiného významu."""
        return self.fold.get(lemma.lower(), lemma.lower())

    def blizka(self, lemma: str) -> list:
        """Všechna lemmata z týchž významových skupin. Nejednoznačné —
        volající si musí být vědom, že „kázat" táhne i „kárat"."""
        out = []
        for skupina in self.skupiny.get(lemma.lower(), ()):
            out.extend(s.lower() for s in skupina if s.lower() != lemma.lower())
        opacne = self.fold.get(lemma.lower())
        if opacne and opacne not in out:
            out.append(opacne)
        return out


class MostLemmat:
    """Lemma → tvary, které v korpusu opravdu stojí.

    Bez tohohle je slovník synonym k ničemu: řekne „hlásat → kázat", jenže
    v korpusu není „kázat", nýbrž „kázal", „kázali", „kázání". Rejstřík se
    staví z korpusu, ne ze slovníku — obsahuje jen to, co se v textu vyskytlo.
    """

    def __init__(self, vety: Iterable):
        self.tvary: dict = {}
        for veta in vety:
            for t in veta:
                lemma = (t.get("lemma") or "").lower()
                if lemma:
                    self.tvary.setdefault(lemma, set()).add(t["form"].lower())

    def __len__(self) -> int:
        return len(self.tvary)

    def formy(self, lemma: str) -> list:
        return sorted(self.tvary.get(lemma.lower(), ()))
