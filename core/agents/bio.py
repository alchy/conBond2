"""Biografická závorka: „Osoba ( datum místo – datum místo )" → narození a úmrtí.

PŘEVZATO Z conBond (`bio.py`). Tam to vzniklo z pozorování, že běžná extrakce
tuhle konstrukci zahodí — podměty se rozpadnou a data nedostanou roli. Tady
platí totéž a je to změřené: **200 vět v korpusu má závorku s rokem a všech
200 nemá jedinou časovou návěsku.** Přitom je to úvodní věta každého článku a
nese narození i úmrtí naráz.

PROČ TO NEDĚLÁ CHRONOS. Chronos závorky přeskakuje a je to tak správně: bez
toho řezu věta „Narodil se … Marii ( 1894 – 1970 ) a Bohumilu ( 1893 … )"
přivěsila roky RODIČŮ k narození protagonisty. Ten řez se tedy neruší —
biografická závorka je jiná konstrukce a čte se ZÁMĚRNĚ, jen tam, kde stojí
hned za jménem a má tvar „něco – něco".

CO SE Z NÍ BERE. Levá půle před pomlčkou je narození, pravá úmrtí; rok je
čtyřmístné číslo, místo je PROPN s `NameType=Geo`. Deterministické, žádný
model.

    Alois Jirásek ( 23. srpna 1851 Hronov – 12. března 1930 Praha )
                    └── narození ────┘      └── úmrtí ─────┘

Vedle typu se přidá i UDÁLOST — `Udal=narozeni`. Bez ní by pole vidělo dva
časy vedle sebe a nepoznalo, který je který; s ní je to dvojí různé místo.
"""

import re
from typing import Optional, Sequence

from .base import Agent, Naveska

# Pomlčka mezi půlkami. En-dash i obyčejná; Wikipedie používá obojí.
POMLCKY = ("–", "—", "-")
OTEVRENI = ("(", "[")
ZAVRENI = (")", "]")

ROK = re.compile(r"^1[0-9]{3}$|^20[0-9]{2}$")


class Bio(Agent):
    jmeno = "bio"
    typ = ""            # typ je na každé návěsce vlastní

    def __init__(self, rok_od: int = 1000, rok_do: int = 2100):
        self.rok_od = rok_od
        self.rok_do = rok_do

    # ---- hledání -----------------------------------------------------
    def najdi(self, veta: Sequence[dict]) -> list:
        zavorka = self.najit_zavorku(veta)
        if zavorka is None:
            return []
        od, do, delici = zavorka
        # Narození a úmrtí se přiznají JEN u definiční věty článku. První
        # verze brala každou závorku za jménem a přivěsila „narození" datům
        # manželky, dcery i létům studia na gymnáziu — přesně ta past, proti
        # které vznikl řez `v_zavorce`. Jinde je to pořád čas a místo, ale
        # čí život to je, nevíme, a tvrdit to by bylo horší než mlčet.
        definicni = self.je_definicni(veta, od, do)
        out = []
        for (a, b), udalost in (((od + 1, delici), "narozeni"),
                                ((delici + 1, do), "umrti")):
            out.extend(self.vytezit(veta, a, b,
                                    udalost if definicni else "zivot"))
        return out

    @staticmethod
    def je_definicni(veta: Sequence[dict], od: int, do: int) -> bool:
        """Úvodní věta životopisu: „Osoba ( … – … ) byl/byla …".

        Dvě podmínky naráz, protože každá sama propouští: jméno na začátku
        věty a spona hned za závorkou.

        HRANICE BYLA SEDM TOKENŮ A BYLA TĚSNÁ. Životopis často začíná
        vsuvkou s jiným jménem:

            Karel Čapek , rodným jménem Karel Antonín Čapek ( 9 . ledna 1890 …
            Božena Němcová , rodným jménem Barbora Novotná , později … ( 4 . února 1820 …

        Závorka je tam až za desátým, respektive čtrnáctým tokenem, takže
        se definiční nepoznala a data se označila jako `Udal=zivot` — tedy
        „nějaký letopočet ze života". Čapek a Němcová pak neměli vytažené
        narození vůbec, ačkoli stojí v první větě článku.

        Šestnáct místo sedmi. Vsuvka „rodným jménem X, později Y" se do
        toho vejde a přitom to pořád znamená ZAČÁTEK věty — spona hned za
        závorkou zůstává druhou podmínkou a ta je ta přísná."""
        if od > 16:
            return False
        po = veta[do + 1] if do + 1 < len(veta) else None
        return bool(po and po["form"].lower() in
                    ("byl", "byla", "bylo", "byli", "je", "jsou"))

    def najit_zavorku(self, veta: Sequence[dict]) -> Optional[tuple]:
        """Závorka hned za jménem, uvnitř s pomlčkou. Vrací (od, do, dělicí).

        „Hned za jménem" je podstatné: bez toho by se chytila každá závorka
        ve větě, včetně těch rodičovských, které Chronos schválně přeskakuje.
        """
        for i, t in enumerate(veta):
            if t["form"] not in OTEVRENI or i == 0:
                continue
            if veta[i - 1]["upos"] not in ("PROPN", "NOUN"):
                continue
            konec = self.najit_konec(veta, i)
            if konec is None:
                continue
            delici = self.najit_delic(veta, i + 1, konec)
            if delici is None:
                continue
            uvnitr = " ".join(veta[j]["form"] for j in range(i + 1, konec))
            if not re.search(r"\b\d{4}\b", uvnitr):
                continue
            return i, konec, delici
        return None

    @staticmethod
    def najit_delic(veta: Sequence[dict], od: int, do: int) -> Optional[int]:
        """Pomlčka, která dělí narození od úmrtí — ne každá pomlčka uvnitř.

        „( 21. prosince 1926 Praha - Libeň – 26. února 2011 Praha )" má
        pomlčky dvě a ta první je uvnitř názvu čtvrti; vzalo se to za dělič a
        z Libně se stalo místo úmrtí. Dělí ta, která má rok na OBOU stranách."""
        kandidati = [j for j in range(od, do) if veta[j]["form"] in POMLCKY]
        def ma_rok(a, b):
            return any(ROK.match(veta[j]["form"]) for j in range(a, b))
        # Dlouhá pomlčka má přednost: rozsah dat se sází en-dashem, kdežto
        # spojovník uvnitř „Praha - Libeň" odděluje části názvu. Bez toho
        # vyšla Libeň jako místo úmrtí.
        dlouhe = [j for j in kandidati if veta[j]["form"] in ("–", "—")]
        for skupina in (dlouhe, kandidati):
            for j in skupina:
                if ma_rok(od, j) and ma_rok(j + 1, do):
                    return j
        # Žijící autor: rok jen vlevo. Pak bere poslední pomlčku, aby se
        # nerozdělilo uvnitř složeného názvu.
        for j in reversed(kandidati):
            if ma_rok(od, j):
                return j
        return kandidati[0] if kandidati else None

    @staticmethod
    def najit_konec(veta: Sequence[dict], od: int) -> Optional[int]:
        hloubka = 0
        for j in range(od, len(veta)):
            if veta[j]["form"] in OTEVRENI:
                hloubka += 1
            elif veta[j]["form"] in ZAVRENI:
                hloubka -= 1
                if hloubka == 0:
                    return j
        return None

    # ---- vytěžení jedné půle -----------------------------------------
    def vytezit(self, veta: Sequence[dict], od: int, do: int,
                udalost: str) -> list:
        """Z půlky závorky rok a místo. Prázdná půle nevrací nic — u žijícího
        autora je pravá strana prázdná a vymýšlet si tam úmrtí by bylo horší
        než mlčet."""
        out = []
        rok = self.najit_rok(veta, od, do)
        if rok is not None:
            i, hodnota = rok
            out.append(Naveska(rozsah=list(range(od, do)), hlava=i,
                               typ="Typ=cas", hodnota=hodnota,
                               zdroj=self.jmeno))
            out.append(Naveska(rozsah=[i], hlava=i, typ=f"Udal={udalost}",
                               zdroj=self.jmeno))
        misto = self.najit_misto(veta, od, do)
        if misto is not None:
            out.append(Naveska(rozsah=[misto], hlava=misto, typ="Typ=misto",
                               hodnota=veta[misto]["form"], zdroj=self.jmeno))
            out.append(Naveska(rozsah=[misto], hlava=misto,
                               typ=f"Udal={udalost}", zdroj=self.jmeno))
        return out

    def najit_rok(self, veta: Sequence[dict], od: int, do: int):
        for j in range(od, do):
            forma = veta[j]["form"]
            if ROK.match(forma) and self.rok_od <= int(forma) <= self.rok_do:
                return j, int(forma)
        return None

    @staticmethod
    def najit_misto(veta: Sequence[dict], od: int, do: int):
        for j in range(od, do):
            t = veta[j]
            if t["upos"] == "PROPN" and any(
                    a == "NameType=Geo" for a in t["acts"]):
                return j
        # Bez NameType=Geo bere poslední PROPN půle — v „1851 Hronov" je
        # jméno města na konci a UDPipe ho jako Geo neoznačí vždycky.
        # OSOBNÍ jméno se ale vyloučí: „Božena ( 1880 – 1951 , provdaná
        # Jelínková )" jinak dá Jelínkovou jako místo úmrtí.
        posledni = None
        for j in range(od, do):
            t = veta[j]
            if t["upos"] != "PROPN":
                continue
            if any(a in ("NameType=Sur", "NameType=Giv") for a in t["acts"]):
                continue
            posledni = j
        return posledni
