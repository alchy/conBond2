"""Převod modelu na JSON. Patří do knihovny, ne do serveru — jiný program
může chtít týž výstup, aniž by kolem něj stavěl HTTP.

Co se posílá ven, je záměrně jen to, co si prohlížeč nespočítá sám. Mřížku
si vykreslí z korpusu, který má; od jádra potřebuje ROZVRŽENÍ řádků (kde
jsou prázdné sloty), přiřazení šablon, vazby a sdílený slovník.

VÝŘEZ. Pole se staví CELÉ — jinak by šablony přestaly být šablonami korpusu
a sdílení by se počítalo z náhodného vzorku. Ven jde jen kousek: spisovatelský
korpus má 59 106 řádků a 26 624 šablon a prohlížeč z toho neudělá nic.

Čísla přitom zůstávají GLOBÁLNÍ. Kdyby se přepočítala na výřez, vypadalo by
to, že korpus je malý a všechno se sdílí — přesně ten omyl, kvůli kterému
dřív vyšel poměr 0.95. U šablon i vazeb se proto vedle výřezu posílá i to,
kolik jich je doopravdy.

Indexy se přečíslují na výřez, aby prohlížeč pracoval s hustými poli a
nemusel o výřezu vědět. Kde v korpusu výřez začíná, řekne `od_vety`.
"""

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

from .field import KORPUSY, Pole
from .lexicon import Slovnik
from .side import Strana


@dataclass(frozen=True)
class Vyrez:
    """Kolik toho jde ven. `vet=None` znamená celý korpus."""
    od_vety: int = 0
    vet: Optional[int] = None

    @property
    def do_vety(self) -> Optional[int]:
        return None if self.vet is None else self.od_vety + self.vet

    def obsahuje(self, veta: int) -> bool:
        if veta < self.od_vety:
            return False
        return self.do_vety is None or veta < self.do_vety

    def je_cely(self) -> bool:
        return self.od_vety == 0 and self.vet is None


CELY = Vyrez()


class Prevod:
    """Přečíslování z globálních indexů na indexy výřezu.

    Drží se to pohromadě v jedné třídě, protože řádky, věty, šablony,
    vazby i slovník musí přečíslovat STEJNĚ — kdyby si to každý dělal sám,
    stačilo by jedno místo zapomenout a hrany by ukazovaly vedle."""

    def __init__(self, strana: Strana, vyrez: Vyrez = CELY):
        self.strana = strana
        self.vyrez = vyrez
        self.radky: dict[int, int] = {}
        self.vety: dict[int, int] = {}
        self._sestavit()

    def _sestavit(self) -> None:
        if self.vyrez.je_cely():
            self.radky = {i: i for i in range(self.strana.tok.pocet_radku())}
            self.vety = {}
            return
        for i, radek in enumerate(self.strana.tok.radky):
            if self.vyrez.obsahuje(radek.veta):
                self.radky[i] = len(self.radky)
                if radek.veta not in self.vety:
                    self.vety[radek.veta] = len(self.vety)

    # ---- převody -----------------------------------------------------
    def radek(self, i: int) -> Optional[int]:
        return self.radky.get(i)

    def veta(self, s: int) -> int:
        return s if self.vyrez.je_cely() else self.vety.get(s, -1)

    def prosit_radky(self, indexy) -> list:
        """Jen řádky uvnitř výřezu, přečíslované."""
        return [self.radky[i] for i in indexy if i in self.radky]

    def pocet_vet(self) -> int:
        if self.vyrez.je_cely():
            return len({r.veta for r in self.strana.tok.radky})
        return len(self.vety)


def radky_strany(strana: Strana, prevod: Prevod) -> list:
    """Rozvržení pole: na řádek dvojice [věta, pořadí tokenu] a null místo
    pořadí tam, kde je prázdný slot z odsazení."""
    return [[prevod.veta(r.veta), None if r.je_prazdny else r.poradi_ve_vete]
            for i, r in enumerate(strana.tok.radky) if i in prevod.radky]


def sablony_strany(strana: Strana, prevod: Prevod,
                   plny_vektor: bool = True) -> dict:
    """Jen šablony, kterých se výřez dotkne. `celkem` je ale z celého pole —
    že vzor sdílí 189 slov, je ta podstatná informace a výřezem se nemění."""
    out = {}
    for oznaceni, info in strana.vypsat_sablony().items():
        radky = prevod.prosit_radky(info["radky"])
        if not radky and not prevod.vyrez.je_cely():
            continue
        out[oznaceni] = {
            "vec": list(info["vec"]) if plny_vektor else list(info["vec"][:3]),
            "delka": len(info["vec"]),
            "tvary": sorted(info["tvary"]),
            "radky": radky,
            "celkem_radku": len(info["radky"]),
            "celkem_tvaru": len(info["tvary"]),
        }
    return out


def vazby_strany(strana: Strana, prevod: Prevod) -> list:
    out = []
    for v in strana.vazby:
        vyskyty = prevod.prosit_radky(v.vyskyty)
        if not vyskyty and not prevod.vyrez.je_cely():
            continue
        out.append({"w": v.tvar_cislo, "t": v.sablona, "vyskyty": vyskyty,
                    "celkem": len(v.vyskyty)})
    return out


def sloty_strany(strana: Strana, prevod: Prevod) -> dict:
    """Offsety slotů na střed. Slot mířící mimo výřez se pošle jako null —
    prohlížeč tak pozná, že tam něco je, jen to nevidí."""
    out = {}
    for i, sloty in strana.sloty_radku.items():
        mistni = prevod.radek(i)
        if mistni is None:
            continue
        out[str(mistni)] = [[prevod.radek(sl.j), sl.d] for sl in sloty]
    return out


def slovnik_ven(slovnik: Slovnik, prevody: Mapping[str, Prevod]) -> list:
    """Počty výskytů jsou GLOBÁLNÍ, seznamy vět jen z výřezu. Tvar, který
    ve výřezu není vůbec, se vynechá — jinak by paleta měla patnáct tisíc
    položek, ze kterých je vidět pár."""
    cely = all(p.vyrez.je_cely() for p in prevody.values())
    out = []
    for p in slovnik.polozky:
        vety = {k: sorted(x for x in (prevody[k].veta(s) for s in p.vety[k])
                          if x >= 0) for k in ("f", "q")}
        if not cely and not (vety["f"] or vety["q"]) and not p.je_prazdny:
            continue
        out.append({
            "tvar": p.tvar,
            "prazdny": p.je_prazdny,
            "radky": {"f": p.radky["f"], "q": p.radky["q"]},
            "vety": vety,
            "sablony": {"f": sorted(p.sablony["f"]), "q": sorted(p.sablony["q"])},
            "jistota": p.spocitat_jistotu(),
        })
    return out


def korpusy_ven(pole: Pole,
                vyrezy: Optional[Mapping[str, Vyrez]] = None) -> dict:
    """Věty tak, jak je vidí jádro — tedy i s hrubými vrstvami a už bez
    toho, co je vypnuté. Prohlížeč jinak vykreslí mřížku, která neodpovídá
    vektoru: sloupec by v katalogu byl a v tokenu ne.

    Čte se to jen přes šev `vypsat_aktivace`, aby export nesahal zdroji
    dovnitř — jiná implementace zdroje odvozuje jinak nebo vůbec."""
    vyrezy = vyrezy or {}
    out = {}
    for strana, jmeno in KORPUSY.items():
        vyrez = vyrezy.get(strana, CELY)
        vety = pole.uloziste.nacist_korpus(jmeno)
        kus = vety if vyrez.je_cely() else vety[vyrez.od_vety:vyrez.do_vety]
        out[jmeno] = [[dict(t, acts=list(pole.zdroj.vypsat_aktivace(t)))
                       for t in veta] for veta in kus]
    return out


def cisla_strany(strana: Strana, prevod: Prevod) -> dict:
    """Čísla jsou z CELÉHO pole. Výřez se hlásí zvlášť, ať je vidět, kolik
    z toho je opravdu na obrazovce."""
    prazdnych, celkem = strana.spocitat_prazdne_sloty()
    return {
        "radku": strana.tok.pocet_radku(),
        "stredu": strana.pocet_stredu(),
        "sablon": strana.pocet_sablon(),
        "vazeb": len(strana.vazby),
        "pomer": round(strana.spocitat_pomer(), 4),
        "slotu": strana.okno.pocet_slotu(),
        "prazdnych_slotu": prazdnych,
        "slotu_celkem": celkem,
        "vet": len({r.veta for r in strana.tok.radky}),
        "vyrez": {
            "od_vety": prevod.vyrez.od_vety,
            "vet": prevod.pocet_vet(),
            "radku": len(prevod.radky),
            "cely": prevod.vyrez.je_cely(),
        },
    }


def strana_ven(strana: Strana, vyrez: Vyrez = CELY,
               plny_vektor: bool = True) -> dict:
    prevod = Prevod(strana, vyrez)
    return {
        "radky": radky_strany(strana, prevod),
        "sablony": sablony_strany(strana, prevod, plny_vektor),
        "vazby": vazby_strany(strana, prevod),
        "sloty": sloty_strany(strana, prevod),
        "cisla": cisla_strany(strana, prevod),
    }


def prehled_sablon(strana: Strana, od: int = 0, pocet: int = 60,
                   razeni: str = "velikost", hledat: str = "") -> dict:
    """Vzory samy o sobě, bez mřížky.

    Tohle je pohled, který velký korpus unese: šablon je 26 624, ale
    zajímavých je pár set a řadí se podle toho, kolik slov je sdílí.
    Řádky se neposílají vůbec — vzor se čte z vektoru a ze seznamu tvarů."""
    polozky = []
    for oznaceni, info in strana.vypsat_sablony().items():
        tvary = sorted(info["tvary"])
        if hledat and not any(hledat in t for t in tvary) \
                and hledat not in oznaceni:
            continue
        polozky.append({
            "id": oznaceni,
            "vec": list(info["vec"]),
            "delka": len(info["vec"]),
            "tvaru": len(tvary),
            "vyskytu": len(info["radky"]),
            "ukazka": tvary[:12],
        })
    klice = {
        "velikost": lambda p: (-p["tvaru"], -p["vyskytu"], p["id"]),
        "vyskyty": lambda p: (-p["vyskytu"], -p["tvaru"], p["id"]),
        "delka": lambda p: (-p["delka"], p["id"]),
        "id": lambda p: p["id"],
    }
    polozky.sort(key=klice.get(razeni, klice["velikost"]))
    return {
        "celkem": len(polozky),
        "od": od,
        "sablony": polozky[od:od + pocet],
        "razeni": razeni,
    }


def pole_ven(pole: Pole, *, s_korpusy: bool = False, plny_vektor: bool = True,
             vyrezy: Optional[Mapping[str, Vyrez]] = None) -> dict:
    """Celý model. `s_korpusy` přiloží i věty — prohlížeč je potřebuje jen
    při prvním načtení, pak si je drží."""
    pole.postavit()
    vyrezy = dict(vyrezy or {})
    ven = {
        "nastaveni": pole.nastaveni.do_slovniku(),
        "klic_mapovani": pole.ziskat_klic_mapovani(),
        "slovnik": None,
        "f": strana_ven(pole.fakta, vyrezy.get("f", CELY), plny_vektor),
        "q": strana_ven(pole.dotazy, vyrezy.get("q", CELY), plny_vektor),
    }
    ven["slovnik"] = slovnik_ven(pole.ziskat_slovnik(), {
        k: Prevod(pole.strana(k), vyrezy.get(k, CELY)) for k in KORPUSY})
    if s_korpusy:
        ven["vertikaly"] = list(pole.vypsat_vertikaly())
        ven["korpusy"] = korpusy_ven(pole, vyrezy)
    return ven
