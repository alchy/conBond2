"""Odpověď na otázku o obsahu korpusu — a hlavně: CO SE AKTIVUJE.

Ne vyhledávání v textu. Otázka se rozloží a každý kus se hledá tím kanálem,
kterým se v poli chová:

    OSOBA je AKTIVACE. Ve 169 ze 170 zlatých vět jméno z otázky VŮBEC NENÍ —
    čeština podmět zahazuje („Narodil se na brněnském předměstí Židenice…")
    a identita sedí jako `Ent=bohumil_hrabal`, kterou doplnila koreference.
    Hledání podle tvaru dalo 1 %, přes aktivaci 100 %.

    SLOVESO je TVAR a najde se ve společném slovníku, který řekne, ve kterých
    větách faktů svítí.

Průnik obojího je POLE ODPOVĚDI; tázací tvar řekne, jaký druh místa v něm
hledat, a agenti Chronos a Topos ta místa označili předem.

DVA STUPNĚ, PROTOŽE JINAK SE TRESTÁ ZÁMĚR. Šablona neidentifikuje jednu
odpověď, ale DRUH místa, kde odpověď leží — „Kde se narodil X?" má trefit
rodiště u všech autorů naráz. Vybrat z pole tu jednu je úloha pro identitu,
ne pro pole, a proto se měří zvlášť.

ZNALOST SE ČTE AŽ TADY, ne v datech. Otázka smí zobecňovat: kdo se ptá na
spisovatele, míří i na Hrabala, protože `hrabal ∈ spisovatel`. Fakt
zobecňovat nesmí — kdyby se expandovalo do dat, vektor se prodlouží a
sdílení podle měření KLESNE.
"""

from collections import defaultdict
from typing import Optional

from .field import Pole
from .language import Jazyk
from .tvrzeni import Znalost


class Odpovidac:
    """Otázka dovnitř, aktivace a kandidáti ven."""

    def __init__(self, pole: Pole, znalost: Optional[Znalost] = None,
                 jazyk: Optional[Jazyk] = None):
        self.pole = pole
        self.znalost = znalost or Znalost()
        self.jazyk = jazyk or Jazyk.nacist()
        self.slovnik = pole.ziskat_slovnik()
        self.vety = pole.uloziste.nacist_korpus("facts")
        self.podle_typu = self._sestavit_navesky()
        self.podle_entity = self._sestavit_entity()

    # ---- rejstříky ---------------------------------------------------
    def _sestavit_navesky(self) -> dict:
        """Věta → typ → rozsahy, které agenti označili."""
        out: dict = defaultdict(lambda: defaultdict(list))
        for vi, veta in enumerate(self.vety):
            for t in veta:
                for n in t.get("navesky", ()):
                    out[vi][n["typ"]].append(tuple(n["rozsah"]))
        return out

    def _sestavit_entity(self) -> dict:
        """Entita → věty, ve kterých o ní je řeč. Klíč je z `Ent=`, protože
        jméno v té větě obvykle nestojí."""
        out: dict = defaultdict(set)
        for vi, veta in enumerate(self.vety):
            for t in veta:
                for a in t["acts"]:
                    if a.startswith("Ent="):
                        out[a[4:]].add(vi)
        return out

    # ---- aktivace ----------------------------------------------------
    def obsahove_tvary(self, text: str) -> list:
        kusy = text.replace("?", " ").replace(".", " ").replace(",", " ").split()
        return [k.lower() for k in kusy if not self.jazyk.je_prazdne(k.lower())]

    def vety_tvaru(self, tvar: str) -> set:
        p = self.slovnik.najit(tvar)
        return set(p.vety["f"]) if p else set()

    def najit_entitu(self, tvary) -> str:
        """Jméno z otázky → klíč entity. Stačí, když sedí příjmení."""
        kusy = {t.lower() for t in tvary}
        nejlepsi, skore = "", 0
        for klic in self.podle_entity:
            shoda = len(set(klic.split("_")) & kusy)
            if shoda > skore:
                nejlepsi, skore = klic, shoda
        return nejlepsi

    def rozsvitit(self, text: str) -> dict:
        tvary = self.obsahove_tvary(text)
        entita = self.najit_entitu(tvary)
        vety_entity = set(self.podle_entity.get(entita, ()))
        zbytek = [t for t in tvary if t not in set(entita.split("_"))]
        kde = {t: self.vety_tvaru(t) for t in zbytek}
        zname = {t: v for t, v in kde.items() if v}
        podle_tvaru = set.intersection(*zname.values()) if zname else set()
        # Prázdný průnik neznamená „nevím" — znamená, že se o TÉHLE osobě
        # tímhle slovesem nemluví. Koreference doplnila entitu jen u 15 %
        # vět korpusu, takže se to stává často a mlčet by bylo horší než
        # ukázat širší pole a přiznat, že je širší.
        siroko = False
        if vety_entity and podle_tvaru:
            prunik = vety_entity & podle_tvaru
            if not prunik:
                prunik, siroko = vety_entity, True
        else:
            prunik = vety_entity or podle_tvaru
        return {"tvary": tvary, "entita": entita, "vet_entity": len(vety_entity),
                "svitici": {t: len(v) for t, v in kde.items()},
                "nezname": [t for t, v in kde.items() if not v],
                "siroko": siroko, "vety": prunik}

    def rozsirit(self, tvar: str) -> set:
        """Věty, které tvar zasáhne PŘES ZNALOST. Potomek se hledá napřed
        jako entita a teprve pak jako tvar — jinak by expanze našla jen věty,
        kde jméno doopravdy stojí, což je u pro-dropu zlomek."""
        vety = set()
        for potomek in self.znalost.potomci(tvar.lower()):
            klic = self.najit_entitu(potomek.split())
            if klic:
                vety |= self.podle_entity[klic]
            else:
                for kus in potomek.split():
                    vety |= self.vety_tvaru(kus)
        return vety

    # ---- odpověď -----------------------------------------------------
    def je_na_obsah(self, text: str) -> bool:
        return self.jazyk.na_co_se_pta(text) is not None

    def odpovedet(self, text: str, se_znalosti: bool = True) -> dict:
        akt = self.rozsvitit(text)
        vety = set(akt["vety"])
        pomohla = set()
        if se_znalosti:
            for t in akt["tvary"]:
                pomohla |= self.rozsirit(t)
            if pomohla:
                vety = pomohla if not vety else ((vety & pomohla) or vety)
        typ = self.jazyk.na_co_se_pta(text)
        nalezy = []
        for vi in sorted(vety):
            for rozsah in self.podle_typu.get(vi, {}).get(typ, ()):
                nalezy.append({"veta": vi, "rozsah": list(rozsah),
                               "text": self.text_rozsahu(vi, rozsah),
                               "kontext": self.text_vety(vi)})
        # Množiny se ven neposílají — nález jde rovnou do JSON pro prohlížeč.
        ven = dict(akt, vety=sorted(akt["vety"])[:200])
        return {"aktivace": ven, "typ": typ, "vet": len(vety),
                "znalost_pomohla": bool(pomohla), "kandidati": nalezy,
                "odpoved": nalezy[0]["text"] if nalezy else None}

    # ---- čtení -------------------------------------------------------
    def text_rozsahu(self, vi: int, rozsah) -> str:
        veta = self.vety[vi]
        return " ".join(veta[j]["form"] for j in rozsah if j < len(veta))

    def text_vety(self, vi: int) -> str:
        return " ".join(t["form"] for t in self.vety[vi]) \
            .replace(" .", ".").replace(" ,", ",")
