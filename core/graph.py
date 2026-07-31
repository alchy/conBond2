"""Graf entit — kdo s kým stojí v jedné větě, a co z toho smí plynout.

PROČ. Odpovídač umí otázky, jejichž odpověď leží v JEDNÉ větě. „Mohla Božena
Němcová znát Emanuela Halmana?" v žádné jedné větě není a přesto se na ni
dá odpovědět: Halman byl asistentem Myslbeka, o Myslbekovi mluví jiná věta,
a mezi tím vede cesta.

Vzdálenost je jediné, co takovou otázku odlišuje od těch, které už umíme.
Hrana je pořád táž hrana.

CESTA NENÍ DŮKAZ, A TOHLE JE TA CELÁ VĚC. Dva lidé v řetězu vět se znát
nemuseli. Kdyby graf odpovídal „ano, znali se", vyrobil by přesvědčivě
znějící nesmysl na každou dvojici jmen v korpusu — a nebylo by to poznat,
protože cesta se vždycky nějaká najde.

Proto se rozlišují TŘI odpovědi a jen jedna z nich je tvrzení:

    doloženo    jedna věta říká obojí naráz            ANO
    cesta       vede řetěz vět, každá s doložením      MOŽNÁ, tady je
    vyloučeno   životy se nepřekrývají                 NE

`vyloučeno` je jediné poctivé „ne", jaké graf umí: kdo zemřel dřív, než se
druhý narodil, se potkat nemohl, ať vede cesta jakkoli. Všechno ostatní je
nanejvýš „možná" — a musí to tak i znít.

VÁHA PODLE VĚTNÉHO ČLENU, převzato z conBondu (`w_subj` 2,0 · `w_obl` 1,0).
Kdo je ve větě podmětem, je jejím tématem; kdo je v určení, je kulisa. Bez
vážení má „narodil se v Praze" stejnou sílu jako „spolupracoval s Hálkem",
a graf se utopí v místech a letopočtech.
"""

from typing import Iterable, Mapping, Optional

from .edges import jmeno as cele_jmeno
from .roles import deprel

# Kolik váží zmínka podle toho, čím ve větě je. Podmět nese téma věty,
# ostatní členy ji jen doplňují.
VAHY = {"nsubj": 2.0, "nsubj:pass": 2.0, "obj": 1.5, "iobj": 1.5,
        "obl": 1.0, "obl:arg": 1.0, "nmod": 1.0, "conj": 0.5}

# Jména, ne slova. Obecné podstatné jméno by z grafu udělalo tezaurus.
JMENNE_UPOS = ("PROPN",)


class Graf:
    """Vážený graf spoluvýskytů jmen, s doložením u každé hrany."""

    def __init__(self):
        self.hrany: dict = {}      # jméno → {jméno: váha}
        self.doklad: dict = {}     # (a, b) → [čísla vět]

    @classmethod
    def postavit(cls, vety: Iterable, nejvys_vet: int = 0) -> "Graf":
        """Z korpusu. Dvě jména v jedné větě = hrana s vahou obou zmínek.

        `nejvys_vet` omezí, kolik doložení se u hrany drží. Nula znamená
        všechna — u velkého korpusu je to hodně paměti a k odpovědi stačí
        pár vět, protože se stejně ukazují jen ony."""
        g = cls()
        for vi, veta in enumerate(vety):
            zminky = {}
            for t in veta:
                if t.get("upos") not in JMENNE_UPOS or deprel(t) == "flat":
                    continue                 # `flat` je část jména, ne zmínka
                # JMÉNO SE SKLÁDÁ TÝMŽ PRAVIDLEM JAKO U HRAN. První verze
                # brala holé lemma tokenu, takže graf měl uzel „jirásek",
                # kdežto životy byly vedené pod „alois jirásek" — a měření
                # pak hlásilo nula doložených dvojic, ačkoli jich jsou
                # tisíce. Vada nebyla v datech, ale v klíči.
                j = cele_jmeno(veta, t)
                if not j:
                    continue
                v = VAHY.get(deprel(t), 0.5)
                zminky[j] = max(zminky.get(j, 0.0), v)
            jmena = sorted(zminky)
            for i, a in enumerate(jmena):
                for b in jmena[i + 1:]:
                    w = zminky[a] * zminky[b]
                    g.hrany.setdefault(a, {})[b] = g.hrany.get(a, {}).get(b, 0.0) + w
                    g.hrany.setdefault(b, {})[a] = g.hrany.get(b, {}).get(a, 0.0) + w
                    d = g.doklad.setdefault((a, b) if a < b else (b, a), [])
                    if not nejvys_vet or len(d) < nejvys_vet:
                        d.append(vi)
        return g

    def __len__(self) -> int:
        return len(self.hrany)

    def doklady(self, a: str, b: str) -> list:
        return self.doklad.get((a, b) if a < b else (b, a), [])

    def cesta(self, a: str, b: str, nejdel: int = 4) -> list:
        """Nejkratší cesta mezi jmény, nebo prázdno.

        Nejkratší, ne nejsilnější: dlouhý řetěz slabých vazeb neznamená
        o nic víc než krátký, a čím delší cesta, tím menší cena. Váhy
        rozhodují až mezi cestami stejné délky — silnější vazba napřed.
        """
        a, b = a.lower(), b.lower()
        if a not in self.hrany or b not in self.hrany:
            return []
        if a == b:
            return [a]
        videno = {a}
        fronta = [[a]]
        while fronta:
            dalsi = []
            for cesta in fronta:
                konec = cesta[-1]
                sousedi = sorted(self.hrany.get(konec, {}).items(),
                                 key=lambda x: -x[1])
                for soused, _w in sousedi:
                    if soused == b:
                        return cesta + [b]
                    if soused in videno or len(cesta) >= nejdel:
                        continue
                    videno.add(soused)
                    dalsi.append(cesta + [soused])
            fronta = dalsi
        return []


def prekryv_zivotu(a: Optional[tuple], b: Optional[tuple]) -> Optional[bool]:
    """Mohli být naživu zároveň?

    `a`, `b` jsou dvojice (narození, úmrtí) v letech; None kdekoli znamená,
    že se to neví. Vrací True / False / None — a to None je podstatné:
    neznámé datum NENÍ důvod říct „ne". Pole je monotónní i tady.
    """
    if not a or not b:
        return None
    (na, za), (nb, zb) = a, b
    if za and nb and za < nb:
        return False
    if zb and na and zb < na:
        return False
    if na and nb:
        return True
    return None


def spojeni(graf: Graf, a: str, b: str, zivoty: Optional[Mapping] = None,
            nejdel: int = 4) -> dict:
    """Odpověď na „mohl A znát B?" — a jen taková, jaká je doložená.

    Pořadí zkoušek není libovolné: nejdřív se vylučuje, potom dokládá,
    a teprve nakonec hledá cesta. Kdyby se hledala napřed, našla by se
    vždycky a časové vyloučení by přišlo pozdě — jako výmluva za odpovědí
    místo místo ní.
    """
    zivoty = zivoty or {}
    a, b = a.lower(), b.lower()
    soucasnici = prekryv_zivotu(zivoty.get(a), zivoty.get(b))
    if soucasnici is False:
        return {"druh": "vylouceno", "cesta": [], "doklad": [],
                "proc": "životy se nepřekrývají"}
    primo = graf.doklady(a, b)
    if primo:
        return {"druh": "dolozeno", "cesta": [a, b], "doklad": primo[:5],
                "soucasnici": soucasnici}
    cesta = graf.cesta(a, b, nejdel=nejdel)
    if not cesta:
        return {"druh": "nevim", "cesta": [], "doklad": []}
    kroky = [{"z": cesta[i], "do": cesta[i + 1],
              "vety": graf.doklady(cesta[i], cesta[i + 1])[:3]}
             for i in range(len(cesta) - 1)]
    return {"druh": "cesta", "cesta": cesta, "kroky": kroky,
            "soucasnici": soucasnici}
