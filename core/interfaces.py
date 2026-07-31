"""Abstraktní metody — jediná místa, kde se smí lišit implementace.

Jádro je natvrdo: odsazení, offsety a to, že šablona vzniká sloučením
stejných vektorů. Co se smí vyměnit, je tohle:

  ZdrojAktivaci    odkud se berou atributy tokenu
  Uloziste         odkud se čte korpus a kam se ukládá mapování
  SkladacVektoru   jak se z okolí udělá vektor
  Slucovac         kdy jsou dva vektory tatáž šablona

Když se v jádře objeví `if` podle druhu dat, znamená to, že tady chybí šev.
"""

from abc import ABC, abstractmethod
from typing import Any, Hashable, Iterable, Mapping, Sequence


class ZdrojAktivaci(ABC):
    """Co token aktivuje. Dnes UDPipe, ale může to být jiný rozbor, ruční
    anotace nebo jiný jazyk — jádro se neptá, kdo aktivace vyrobil."""

    @abstractmethod
    def vypsat_aktivace(self, token: Mapping) -> Sequence[str]:
        """Aktivace tokenu, odfiltrované a v KANONICKÉM pořadí. Pořadí je
        významné: vektor je posloupnost, takže táž sada jinak seřazená by
        dala jinou šablonu."""

    @abstractmethod
    def je_interpunkce(self, token: Mapping) -> bool:
        """Při normalizovaném zrnu tyhle tokeny do pole nejdou."""

    @abstractmethod
    def urcit_tvar(self, token: Mapping) -> str:
        """Klíč tvaru do slovníku, už podle zvoleného zrna."""


class Uloziste(ABC):
    """Odkud se čte a kam se píše. Dnes JSON soubory; u větších dat to může
    být databáze nebo proud, aniž by o tom jádro vědělo."""

    @abstractmethod
    def nacist_vertikaly(self) -> Sequence[Mapping]:
        """Sloupce pole: [{'a': 'NOUN', 'g': 'UPOS'}, …]"""

    @abstractmethod
    def nacist_korpus(self, strana: str) -> Sequence[Sequence[Mapping]]:
        """Věty jedné strany; `strana` je 'facts' nebo 'query'."""

    @abstractmethod
    def nacist_mapovani(self, klic: str) -> Sequence[Mapping]:
        """Dvojice pro dvojici poloměrů, klíč tvaru q<rq>f<rf>."""

    @abstractmethod
    def ulozit_mapovani(self, klic: str, dvojice: Iterable[Mapping]) -> None:
        ...


class SkladacVektoru(ABC):
    """Jak se z okolí udělá vektor. Dnes 'offset:aktivace' jako řetězec;
    jinou implementací může být řídký číselný vektor nebo hash."""

    @abstractmethod
    def popsat_slot(self, offset: int, aktivace: Sequence[str]) -> Sequence[Any]:
        """Co jeden slot přispěje do vektoru."""

    @abstractmethod
    def slozit_vektor(self, casti: Iterable[Sequence[Any]]) -> Any:
        """Poskládá příspěvky slotů dohromady."""

    @abstractmethod
    def spocitat_klic(self, vektor: Any) -> Hashable:
        """Klíč pro slučování. Týž klíč = tentýž vzor."""

    @abstractmethod
    def vypsat_vektor(self, vektor: Any) -> Sequence[str]:
        """Vektor k zobrazení."""


class Slucovac(ABC):
    """Kdy jsou dva vektory tatáž šablona. Dnes přesná shoda klíče; jinou
    implementací může být podobnost nad prahem."""

    @abstractmethod
    def zacit_sadu(self, predpona: str) -> None:
        """Nová sada šablon. Předpona 't' pro fakta, 'q' pro dotazy — id
        jsou pak od sebe rozeznatelná na první pohled."""

    @abstractmethod
    def zaradit(self, vektor: Any, klic: Hashable) -> str:
        """Vrátí id šablony, pod kterou vektor spadá; novou v případě
        potřeby založí."""

    @abstractmethod
    def vypsat_sablony(self) -> Mapping[str, Any]:
        """id → {'vec': …, 'tvary': set, 'radky': list}"""
