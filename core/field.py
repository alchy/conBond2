"""Fasáda celého průchodu. Tohle si naimportuje program, který chce pole.

    from core import Pole, Nastaveni, UlozisteSouboru

    pole = Pole(UlozisteSouboru("data"))
    pole.nastaveni.polomer_dotazu = 4      # nastaví se jednou a platí
    pole.postavit()
    print(pole.dotazy.pocet_sablon())

Poloměr se nevleče každým voláním — drží ho Nastaveni. Setter jen poznamená,
že model zestaral; přepočítá se, až si o výsledek někdo řekne.
"""

from typing import Mapping, Optional, Sequence

from .settings import Nastaveni
from .window import Okno
from .interfaces import Sitko, SkladacVektoru, Slucovac, Uloziste, ZdrojAktivaci
from .lexicon import Slovnik
from .log import log
from .side import Strana
from .sieve import SitkoStredu, filtruje_stred
from .flow import Tok
from .sources import SkladacRetezcem, SlucovacShodou, ZdrojZTokenu

PREDPONY = {"f": "t", "q": "q"}
KORPUSY = {"f": "facts", "q": "query"}


class Pole:
    def __init__(self, uloziste: Uloziste, nastaveni: Optional[Nastaveni] = None, *,
                 zdroj: Optional[ZdrojAktivaci] = None,
                 skladac: Optional[SkladacVektoru] = None,
                 slucovace: Optional[Mapping[str, Slucovac]] = None,
                 sitko: Optional[Sitko] = None):
        self.uloziste = uloziste
        self.nastaveni = nastaveni or Nastaveni()
        self._zdroj_zvenku = zdroj
        self._sitko_zvenku = sitko
        self.skladac = skladac or SkladacRetezcem()
        self.slucovace = dict(slucovace) if slucovace else {
            "f": SlucovacShodou(), "q": SlucovacShodou()}
        self.zdroj: Optional[ZdrojAktivaci] = None
        self.sitko: Optional[Sitko] = None
        self.slovnik: Optional[Slovnik] = None
        self.strany: dict[str, Strana] = {}

    # ---- stavba ------------------------------------------------------
    def postavit(self, vzdy: bool = False) -> "Pole":
        """Celý průchod. Když se od minule nic nezměnilo, nedělá nic."""
        if not (vzdy or self.nastaveni.zestaralo):
            log.debug("model je čerstvý, nepřepočítávám")
            return self
        with log.krok("průchod", r_f=self.nastaveni.polomer_faktu,
                      r_q=self.nastaveni.polomer_dotazu,
                      syrove=self.nastaveni.syrove, typy=self.nastaveni.typy):
            self.zdroj = self.pripravit_zdroj()
            self.sitko = self.pripravit_sitko()
            with log.krok("rozprostření vět"):
                toky = {k: self.rozprostrit(k) for k in KORPUSY}
            with log.krok("sdílený slovník"):
                self.slovnik = self.naplnit_slovnik(toky)
                log.info("slovník hotov", tvaru=len(self.slovnik),
                         v_obou=len(self.slovnik.vypsat_tvary_v_obou()),
                         nejistych=len(self.slovnik.vypsat_nejiste()))
            self.strany = {}
            for k in KORPUSY:
                with log.krok(f"strana {k}"):
                    self.strany[k] = self.postavit_stranu(k, toky[k])
                    st = self.strany[k]
                    log.info("strana hotova", strana=k, radku=st.tok.pocet_radku(),
                             stredu=st.pocet_stredu(), sablon=st.pocet_sablon(),
                             vazeb=len(st.vazby), pomer=st.spocitat_pomer())
            self.nastaveni.oznacit_cerstvym()
        return self

    def pripravit_zdroj(self) -> ZdrojAktivaci:
        if self._zdroj_zvenku is not None:
            return self._zdroj_zvenku
        return ZdrojZTokenu(self.uloziste.nacist_vertikaly(),
                            typy=self.nastaveni.typy,
                            syrove=self.nastaveni.syrove)

    def pripravit_sitko(self) -> Sitko:
        """Vertikály sítko potřebuje kvůli skupinám — `FEATS` propustí celou
        skupinu, ne jedno jméno."""
        if self._sitko_zvenku is not None:
            return self._sitko_zvenku
        return SitkoStredu(self.nastaveni.stred_atributy,
                           self.uloziste.nacist_vertikaly())

    def rozprostrit(self, strana: str) -> Tok:
        vety = self.uloziste.nacist_korpus(KORPUSY[strana])
        log.debug("rozprostírám", strana=strana, vet=len(vety),
                  polomer=self.nastaveni.ziskat_polomer(strana))
        return Tok(self.zdroj, self.nastaveni.ziskat_polomer(strana),
                   syrove=self.nastaveni.syrove).rozprostrit(vety)

    def naplnit_slovnik(self, toky: Mapping[str, Tok]) -> Slovnik:
        """Slovník je společný a plní se z OBOU stran dřív, než se staví
        šablony — jinak by strana, která přijde druhá, neměla kam zapsat."""
        slovnik = Slovnik(self.zdroj)
        for strana in KORPUSY:
            slovnik.naplnit_z_toku(toky[strana], strana)
        return slovnik

    def postavit_stranu(self, strana: str, tok: Tok) -> Strana:
        okno = Okno(self.nastaveni.ziskat_polomer(strana),
                    self.nastaveni.stred_uvnitr)
        if filtruje_stred(self.sitko) and not okno.zasahuje(0):
            log.info("sítko filtruje střed, ale střed není v okně — nefiltruje "
                     "se nic; chybí stred_uvnitr", strana=strana, sitko=repr(self.sitko))
        return Strana(strana, PREDPONY[strana], tok, okno, self.zdroj,
                      self.skladac, self.slucovace[strana], self.slovnik,
                      self.sitko).postavit()

    # ---- čtení -------------------------------------------------------
    @property
    def fakta(self) -> Strana:
        return self.strana("f")

    @property
    def dotazy(self) -> Strana:
        return self.strana("q")

    def strana(self, k: str) -> Strana:
        self.postavit()
        return self.strany[k]

    def ziskat_slovnik(self) -> Slovnik:
        self.postavit()
        return self.slovnik

    # ---- pohodlné nastavení -----------------------------------------
    def nastavit_polomery(self, fakta: int, dotazy: int) -> "Pole":
        self.nastaveni.nastavit_polomer("f", fakta)
        self.nastaveni.nastavit_polomer("q", dotazy)
        return self

    def ziskat_klic_mapovani(self) -> str:
        return self.nastaveni.klic_mapovani()

    def nacist_mapovani(self) -> Sequence[Mapping]:
        return self.uloziste.nacist_mapovani(self.ziskat_klic_mapovani())

    def ulozit_mapovani(self, dvojice) -> None:
        self.uloziste.ulozit_mapovani(self.ziskat_klic_mapovani(), dvojice)
