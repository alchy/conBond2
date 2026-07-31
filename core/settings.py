"""Nastavení průchodu. Nastaví se jednou a platí — nevleče se každým voláním.

Setter nikdy nepočítá; jen si poznamená, že model zestaral. Přepočítá se až
tehdy, když si o výsledek někdo řekne. Kdyby setter přepočítával sám,
nastavení tří věcí za sebou by průchod spustilo třikrát.

POLOMĚRY JSOU DVA A SMÍ SE LIŠIT. Dotaz může mít jiné r než fakt, protože se
vektory obou stran nikdy neporovnávají přímo — mapování je kotvené na
tvarech. Kdyby se párovaly vektory, musela by být r shodná.

STŘED MÁ DVĚ PÁČKY, NE JEDNU. `stred_uvnitr` říká, jestli je offset 0 vůbec
slot; `stred_atributy` říká, co z něj projde. Celý střed uvnitř zabije
sdílení, celý venku zneviditelní zápor a čas — viz sieve.py.
"""

MAX_POLOMER = 8

# Výchozí je to, co je změřeně nejlepší — jinak by se každý musel trefit sám.
# `NameType` na středu stojí 2 body sdílení (59 % → 57 %) a zvedne čistotu
# šablon nesoucích místo z 22 % na 98 %: „v Praze" a „v bezvědomí" mají
# identického souseda a rozlišuje je právě to, co sedí NA STŘEDU.
VYCHOZI_STRED = ("NameType",)


class Nastaveni:
    def __init__(self, polomer_faktu: int = 1, polomer_dotazu: int = 1, *,
                 syrove: bool = False, stred_uvnitr: bool = False,
                 typy: bool = True, stred_atributy=VYCHOZI_STRED):
        self._polomer = {"f": 0, "q": 0}
        self.polomer_faktu = polomer_faktu
        self.polomer_dotazu = polomer_dotazu
        self._syrove = bool(syrove)
        self._stred_uvnitr = bool(stred_uvnitr)
        self._typy = bool(typy)
        self._stred_atributy: tuple = ()
        self.stred_atributy = stred_atributy
        self.zestaralo = True

    # ---- poloměry ----------------------------------------------------
    @staticmethod
    def overit_polomer(r: int) -> int:
        r = int(r)
        if not 0 <= r <= MAX_POLOMER:
            raise ValueError(f"poloměr musí být 0–{MAX_POLOMER}, dostal jsem {r}")
        return r

    def ziskat_polomer(self, strana: str) -> int:
        return self._polomer[strana]

    def nastavit_polomer(self, strana: str, r: int) -> "Nastaveni":
        if strana not in self._polomer:
            raise KeyError(f"strana je 'f' nebo 'q', ne {strana!r}")
        r = self.overit_polomer(r)
        if self._polomer[strana] != r:
            self._polomer[strana] = r
            self.zestaralo = True
        return self

    @property
    def polomer_faktu(self) -> int:
        return self._polomer["f"]

    @polomer_faktu.setter
    def polomer_faktu(self, r: int) -> None:
        self.nastavit_polomer("f", r)

    @property
    def polomer_dotazu(self) -> int:
        return self._polomer["q"]

    @polomer_dotazu.setter
    def polomer_dotazu(self, r: int) -> None:
        self.nastavit_polomer("q", r)

    # ---- ostatní přepínače -------------------------------------------
    def _prepnout(self, jmeno: str, hodnota: bool) -> None:
        hodnota = bool(hodnota)
        if getattr(self, jmeno) != hodnota:
            setattr(self, jmeno, hodnota)
            self.zestaralo = True

    @property
    def syrove(self) -> bool:
        """Zrno textu. Syrově = s interpunkcí a rozlišením velikosti písmen."""
        return self._syrove

    @syrove.setter
    def syrove(self, v: bool) -> None:
        self._prepnout("_syrove", v)

    @property
    def stred_uvnitr(self) -> bool:
        """Je střed součástí vlastního vektoru? Když ne, je vzor obálkou
        okolí bez jediného slova uvnitř."""
        return self._stred_uvnitr

    @stred_uvnitr.setter
    def stred_uvnitr(self, v: bool) -> None:
        self._prepnout("_stred_uvnitr", v)

    @property
    def stred_atributy(self) -> tuple:
        """Co ze středu smí do vlastního vektoru. Prázdné = všechno.

        Jméno se píše jako přesná aktivace (`Polarity=Neg`), jako atribut
        (`Polarity`), nebo jako skupina vertikál (`FEATS`)."""
        return self._stred_atributy

    @stred_atributy.setter
    def stred_atributy(self, hodnoty) -> None:
        # Řetězec je častý překlep — „Polarity" by se rozpadlo na písmena.
        if isinstance(hodnoty, str):
            hodnoty = [k.strip() for k in hodnoty.split(",") if k.strip()]
        nove = tuple(dict.fromkeys(str(h) for h in hodnoty or ()))
        if nove != self._stred_atributy:
            self._stred_atributy = nove
            self.zestaralo = True
        # Dvě páčky, které si musí odpovídat: filtrovat střed, který v okně
        # není, nedává smysl. Setter tu nic nepočítá, jen srovnává nastavení.
        if nove and not self._stred_uvnitr:
            self.stred_uvnitr = True

    @property
    def typy(self) -> bool:
        """Významový typ. Vypnutý musí zmizet i z pole, ne jen z vektoru."""
        return self._typy

    @typy.setter
    def typy(self, v: bool) -> None:
        self._prepnout("_typy", v)

    # ---- odvozené ----------------------------------------------------
    def klic_mapovani(self) -> str:
        """Mapování má vlastní store pro každou dvojici poloměrů: šablony
        dotazů závisí na r_q, šablony faktů na r_f."""
        return f"q{self.polomer_dotazu}f{self.polomer_faktu}"

    def oznacit_cerstvym(self) -> None:
        self.zestaralo = False

    def do_slovniku(self) -> dict:
        return {
            "polomer_faktu": self.polomer_faktu,
            "polomer_dotazu": self.polomer_dotazu,
            "syrove": self.syrove,
            "stred_uvnitr": self.stred_uvnitr,
            "stred_atributy": list(self.stred_atributy),
            "typy": self.typy,
        }

    @classmethod
    def ze_slovniku(cls, d: dict) -> "Nastaveni":
        return cls(
            polomer_faktu=int(d.get("polomer_faktu", 1)),
            polomer_dotazu=int(d.get("polomer_dotazu", 1)),
            syrove=bool(d.get("syrove", False)),
            stred_uvnitr=bool(d.get("stred_uvnitr", False)),
            stred_atributy=d.get("stred_atributy", ()),
            typy=bool(d.get("typy", True)),
        )

    def __repr__(self) -> str:
        stred = "mimo"
        if self.stred_uvnitr:
            stred = ",".join(self.stred_atributy) or "celý"
        return (f"Nastaveni(r_f={self.polomer_faktu}, r_q={self.polomer_dotazu}, "
                f"syrove={self.syrove}, stred={stred}, typy={self.typy})")
