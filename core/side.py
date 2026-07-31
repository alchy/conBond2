"""Krok 4 workflow: jedna strana pole — fakta nebo dotazy.

Šablony a vazby má každá strana VLASTNÍ; slovník je společný a dostane se
sem hotový. Poloměr se stranám smí lišit: dotaz může mít jiné r než fakt,
protože se vektory obou stran nikdy neporovnávají přímo — mapování je
kotvené na tvarech.
"""

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .window import Okno, Slot
from .interfaces import Sitko, SkladacVektoru, Slucovac, ZdrojAktivaci
from .lexicon import Slovnik
from .log import log
from .sieve import SitkoVse
from .flow import Tok


@dataclass
class Vazba:
    """Dvojice (slovo, šablona) — tatáž tabulka, jakou drží kód:
    links[(w_id, t_id, zrno)] → výskyty"""
    tvar_cislo: int
    sablona: str
    vyskyty: list = field(default_factory=list)


class Strana:
    def __init__(self, oznaceni: str, predpona: str, tok: Tok, okno: Okno,
                 zdroj: ZdrojAktivaci, skladac: SkladacVektoru, slucovac: Slucovac,
                 slovnik: Slovnik, sitko: Sitko = None):
        self.oznaceni = oznaceni
        self.predpona = predpona
        self.tok = tok
        self.okno = okno
        self.zdroj = zdroj
        self.skladac = skladac
        self.slucovac = slucovac
        self.slovnik = slovnik
        self.sitko = sitko or SitkoVse()
        self.slovo_radku: dict[int, tuple[int, str]] = {}
        self.sloty_radku: dict[int, list[Slot]] = {}
        self.vazby: list[Vazba] = []

    # ---- stavba ------------------------------------------------------
    def postavit(self) -> "Strana":
        self.slucovac.zacit_sadu(self.predpona)
        for i, radek in self.tok.vypsat_stredy():
            self.zaradit_stred(i, radek)
        self.sestavit_vazby()
        return self

    def zaradit_stred(self, i: int, radek) -> str:
        sloty = self.okno.urcit_sloty(i)
        self.sloty_radku[i] = sloty
        vektor = self.slozit_vektor(sloty)
        oznaceni = self.slucovac.zaradit(vektor, self.skladac.spocitat_klic(vektor))
        tvar = self.zdroj.urcit_tvar(radek.token)
        self.pripsat_k_sablone(oznaceni, tvar, i)
        self.slovo_radku[i] = (self.slovnik.cislo(tvar), oznaceni)
        log.debug("střed zařazen", radek=i, tvar=tvar, sablona=oznaceni,
                  slotu=len(sloty), delka_vektoru=len(vektor))
        return oznaceni

    def slozit_vektor(self, sloty: Sequence[Slot]):
        return self.skladac.slozit_vektor(
            self.skladac.popsat_slot(sl.d, self.aktivace_slotu(sl)) for sl in sloty)

    def aktivace_slotu(self, slot: Slot) -> list[str]:
        """Prázdný slot i slot mimo pole nepřispějí ničím — skládač si
        z toho udělá ∅. Co projde dál, rozhodne sítko podle offsetu."""
        radek = self.tok.radek(slot.j)
        if radek is None or radek.je_prazdny:
            return []
        return list(self.sitko.propustit(
            slot.d, self.zdroj.vypsat_aktivace(radek.token)))

    def pripsat_k_sablone(self, oznaceni: str, tvar: str, radek: int) -> None:
        info = self.slucovac.vypsat_sablony()[oznaceni]
        info["tvary"].add(tvar)
        info["radky"].append(radek)
        self.slovnik.zapsat_sablonu(tvar, self.oznaceni, oznaceni)

    def sestavit_vazby(self) -> list[Vazba]:
        podle_dvojice: dict[tuple, Vazba] = {}
        for i in sorted(self.slovo_radku):
            cislo, oznaceni = self.slovo_radku[i]
            klic = (cislo, oznaceni)
            if klic not in podle_dvojice:
                podle_dvojice[klic] = Vazba(tvar_cislo=cislo, sablona=oznaceni)
            podle_dvojice[klic].vyskyty.append(i)
        self.vazby = list(podle_dvojice.values())
        log.debug("vazby sestaveny", strana=self.oznaceni, vazeb=len(self.vazby),
                  sablon=len(self.vypsat_sablony()))
        return self.vazby

    # ---- čtení -------------------------------------------------------
    def vypsat_sablony(self) -> Mapping[str, dict]:
        return self.slucovac.vypsat_sablony()

    def pocet_sablon(self) -> int:
        return len(self.vypsat_sablony())

    def pocet_stredu(self) -> int:
        return len(self.slovo_radku)

    def spocitat_pomer(self) -> float:
        """Šablon na střed. Blíží-li se jedné, nesdílí vzor skoro nikdo."""
        stredu = self.pocet_stredu()
        return self.pocet_sablon() / stredu if stredu else 0.0

    def vypsat_vazby_sablony(self, oznaceni: str) -> list[Vazba]:
        """Zpětný odkaz: které vazby na tuhle šablonu ukazují."""
        return [v for v in self.vazby if v.sablona == oznaceni]

    def spocitat_prazdne_sloty(self) -> tuple[int, int]:
        prazdnych = celkem = 0
        for sloty in self.sloty_radku.values():
            for sl in sloty:
                celkem += 1
                radek = self.tok.radek(sl.j)
                if radek is None or radek.je_prazdny:
                    prazdnych += 1
        return prazdnych, celkem
