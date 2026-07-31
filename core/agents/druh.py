"""Druh — čtvrtý druh odpovědi vedle času, místa a počtu: „co to je".

VZNIKLO Z DOTAZU, KTERÝ PROPADL. „Kdo je Ježíš?" odpovědělo „zatím nic
nevím", ačkoli korpus o Ježíšovi mluví v 557 větách a přímo říká, kdo to
je. Otázka totiž šla do ZNALOSTI (vztahy zadané dialogem) a nikdy do POLE,
a pole navíc žádný druh odpovědi „co to je" nemělo.

KONSTRUKCE. Spona v UD nevisí na slovese — jmenný přísudek JE kořen a spona
na něm visí jako `cop`:

    Ježíš  je   Kristus            Alois Jirásek ( … ) byl  prozaik
      │     │      │                     │              │      │
    nsubj  cop   ROOT                  nsubj           cop   ROOT

Token, na kterém visí `cop`, je tedy jmenný přísudek — a to je odpověď na
„kdo/co to je". Deterministické, žádný model.

PODMĚT SE PAMATUJE, ALE MIMO AKTIVACE. Ve větě „Kdo je lhář, ne-li ten, kdo
popírá, že Ježíš je Kristus?" jsou jmenné přísudky dva — `lhář` a `Kristus`
— a jen jeden z nich je odpověď na otázku po Ježíšovi. Čí je který, se proto
ukládá do hodnoty; do vektoru to nesmí, jinak by vznikl sloupec na každé
jméno v korpusu.

CO SE VYNECHÁVÁ. Zájmeno jako přísudek („to je on") neříká nic a tázací
věta („Kdo je lhář?") taky ne — ta se ptá, neodpovídá.

ZÁPOR JE JINÝ TYP, NE ZAHOZENÝ FAKT. Na „Kdo je Božena Němcová?" padla
odpověď „realistkou" — z věty

    Podle Šaldy proto NENÍ Němcová realistkou, měříme-li realismus tím…

Text říká pravý opak toho, co odpovídač vrátil. Zápor přitom nikde nechybí:
spona `není` nese `Polarity=Neg`, jen se na ni nikdo nedíval.

Zahodit takovou větu by bylo špatně dvakrát — pole je monotónní a informace
„realistkou NENÍ" je plnohodnotná. Dostane proto vlastní typ `Typ=druh_ne`.
Na „Kdo je?" se nenabídne, protože se ptá na `Typ=druh`, a přitom v poli
zůstane adresovatelná.

Je to tentýž nález, jaký ukazuje `scripts/ukazka.py` u šablon: nejhorší
případ není spor, ale ticho — chyba, která se netváří jako chyba.
"""

from typing import Optional, Sequence

from .base import Agent, Naveska

# Přísudek, který nic neříká: zájmena a číslovky.
NEVHODNE_UPOS = ("PRON", "DET", "NUM", "PUNCT", "ADP", "AUX", "PART")

# Jmenný přísudek stojí v češtině v NOMINATIVU („je prozaik") nebo
# v INSTRUMENTÁLU („byl nositelem"). Jiný pád znamená, že se rozbor spletl
# a spona visí na něčem jiném — bez tohohle řezu prolezlo „Od roku 1909 byl
# v penzi" jako by druhem bylo „roku".
PADY_PRISUDKU = ("Case=Nom", "Case=Ins")


class Druh(Agent):
    jmeno = "druh"
    typ = "Typ=druh"
    typ_zapor = "Typ=druh_ne"

    def najdi(self, veta: Sequence[dict]) -> list:
        if self.je_tazaci(veta):
            return []
        podle_id = {t.get("id"): t for t in veta if t.get("id") is not None}
        out = []
        for t in veta:
            if not self.ma_sponu(veta, t):
                continue
            if t["upos"] in NEVHODNE_UPOS or not self.je_prisudkovy_pad(t):
                continue
            podmet = self.podmet(veta, t)
            typ = self.typ_zapor if self.je_zaporna(veta, t) else self.typ
            out.append(Naveska(
                rozsah=self.rozsah_prisudku(veta, t, podle_id),
                hlava=veta.index(t), typ=typ,
                hodnota={"tvar": t["form"],
                         "komu": self.cele_jmeno(veta, podmet)},
                zdroj=self.jmeno))
        return out

    # ---- rozpoznání --------------------------------------------------
    @staticmethod
    def ma_sponu(veta: Sequence[dict], t: dict) -> bool:
        """Visí na tomhle tokenu spona? Pak je to jmenný přísudek."""
        return any(x.get("head") == t.get("id") and "cop" in x["acts"]
                   for x in veta)

    @staticmethod
    def je_zaporna(veta: Sequence[dict], t: dict) -> bool:
        """Nese spona zápor? „není realistkou" je tvrzení o tom, čím ta
        osoba NENÍ — a to je jiný fakt, ne slabší varianta téhož."""
        return any(x.get("head") == t.get("id") and "cop" in x["acts"]
                   and "Polarity=Neg" in x["acts"] for x in veta)

    @staticmethod
    def podmet(veta: Sequence[dict], t: dict) -> Optional[dict]:
        """Podmět jmenného přísudku — tedy ten, o kom se to říká."""
        for x in veta:
            if x.get("head") == t.get("id") and (
                    "nsubj" in x["acts"] or "nsubj:pass" in x["acts"]):
                return x
        return None

    @staticmethod
    def je_prisudkovy_pad(t: dict) -> bool:
        """Nominativ, instrumentál, nebo pád vůbec nevyjádřený (přídavná
        jména a cizí slova ho nemají)."""
        pady = [a for a in t["acts"] if a.startswith("Case=")]
        return not pady or any(p in PADY_PRISUDKU for p in pady)

    @staticmethod
    def cele_jmeno(veta: Sequence[dict], podmet: Optional[dict]) -> Optional[str]:
        """Podmět i s příjmením. `nsubj` ukazuje na „Alois" a „Jirásek" na
        něm visí přes `flat`; bez toho by odpověď patřila všem Aloisům."""
        if podmet is None:
            return None
        kusy = [podmet["form"]]
        for x in veta:
            if x.get("head") == podmet.get("id") and "flat" in x["acts"]:
                kusy.append(x["form"])
        return " ".join(kusy).lower()

    @staticmethod
    def je_tazaci(veta: Sequence[dict]) -> bool:
        """Tázací věta se ptá, neodpovídá. „Kdo je lhář?" není tvrzení."""
        return any(t["form"] == "?" for t in veta)

    @staticmethod
    def rozsah_prisudku(veta: Sequence[dict], t: dict, podle_id: dict) -> list:
        """Přísudek i s tím, co ho blíže určuje: „český prozaik", ne „prozaik".

        Bere se jen shodný přívlastek nalevo — „byl prozaik, dramatik
        a učitel" má další členy jako `conj` a ty jsou vlastní odpovědi."""
        i = veta.index(t)
        rozsah = [i]
        j = i - 1
        while j >= 0:
            x = veta[j]
            if x.get("head") != t.get("id") or "amod" not in x["acts"]:
                break
            rozsah.insert(0, j)
            j -= 1
        return rozsah
