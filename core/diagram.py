"""Šipkový diagram — systém se k řešení DOPRACUJE, místo aby ho vyhledal.

ODKUD. Bartlová, *Metody řešení slovních úloh pomocí logiky* (PedF UK 2014),
kap. 4.4. Úloha se vyřeší tak, že se najdou atomární výroky, každý dostane
uzel spolu se svou negací, implikace se nakreslí jako šipky a diagram se
pak obarví od toho, co je dané.

PROČ TO NENÍ DALŠÍ METODA, ALE SPOLEČNÝ TVAR. Odpovídač dosud uměl jen
vyhledat: rozsvítit pole a vzít, co v něm leží. Otázka bez přímého faktu
propadla. Diagram je mechanismus, do kterého spadnou všechna tři patra
odpovědi — a co je podstatnější, spadnou tam jako TOTÉŽ:

    přímý fakt         uzel obarvený korpusem
    složený fakt       řetěz šipek (tchán = otec ∘ manžel)
    vyloučení rozměrem šipka do negace (disjunktní intervaly ⇒ ¬znal)
    naučené v dialogu  šipka přidaná za běhu
    zápor z korpusu    `Typ=druh_ne` je rovnou uzel ¬

Žádná z těch věcí nepotřebuje vlastní větev. Všechny jsou šipka.

ATOM NENÍ NÁLEPKA, JE TO `predikát(argument)`. V učebnici se výroky značí
písmeny — j, k, t — a vypadá to, že je musí pojmenovat člověk. Nemusí:
všechny tři mají týž tvar `doma(osoba)`, liší se jen argumentem. Uzly se
proto jmenují `doma(jakub)`, ne `j`, a tím se z ručního značkování stává
táž úloha, jakou pole už umí: šablona je predikát, kandidáti jsou hodnoty.

DVĚ CESTY K ZÁVĚRU, A KAŽDÁ UMÍ NĚCO JINÉHO.

    obarvit()   propagace od daného      rychlá, ale potřebuje první barvu
    modely()    zkusit všechny možnosti  úplná, ale 2^n

Úloha o vnukovi ukazuje, proč nestačí ta první: nedáno NIC, a přesto
z ní plyne, že někdo je doma. Žádný jednotlivý výrok vynucený není —
to se pozná až rozborem případů.

DVĚ PRAVIDLA, NIC VÍC. Diagram se obarvuje jen jimi a obě jsou v úloze
o věštkyni potřeba:

    modus ponens    p ⇒ q,  p platí       ⇒  q platí
    modus tollens   p ⇒ q,  q neplatí     ⇒  p neplatí

Modus tollens je ten, na kterém to celé stojí. Kdyby se šipky četly jen
dopředu, z „zaplatil jsem" by vyšlo, že se dozvím pravdu, a tím by to
skončilo. Že nejsem hloupý, plyne až zpětně: hloupý neplatí, protože
kdyby platil, nezaplatil bych — a já zaplatil.

V klasickém diagramu se to kreslí jako obrácená šipka mezi negacemi
(p ⇒ q dává ¬q ⇒ ¬p). Tady se obrácené šipky nedoplňují do dat, ale čtou
se při obarvování; jinak by se graf zdvojnásobil a každý spor by se hlásil
dvakrát.

KAŽDÝ ZÁVĚR NESE SVŮJ DŮVOD. Uzel si pamatuje, odkud barvu dostal —
stejně jako kandidát odpovědi nese svou větu. Bez toho je diagram jen
rychlejší způsob, jak si vymyslet výsledek.

SPOR SE HLÁSÍ, NEPŘEPISUJE. Když má uzel dostat obojí barvu, znamená to,
že si vstupy odporují. Vybrat jednu a jet dál je přesně ta tichá chyba,
kterou tenhle projekt honí jinde — proto se spor vrátí volajícímu.
"""

from typing import Iterable, Mapping, Optional, Sequence

PLATI, NEPLATI = True, False


def negace(uzel: str) -> str:
    """¬¬p je p. Bez toho by dvojitá negace založila třetí uzel o tomtéž."""
    return uzel[1:] if uzel.startswith("¬") else "¬" + uzel


def zaklad(uzel: str) -> str:
    return uzel.lstrip("¬")


class Diagram:
    """Uzly jsou atomární výroky a jejich negace, šipky jsou implikace."""

    def __init__(self):
        self.sipky: list = []            # (z, do, důvod)
        self.uzly: set = set()

    def implikace(self, z: str, do: str, duvod: str = "") -> "Diagram":
        self.sipky.append((z, do, duvod))
        self.uzly.update({z, do, negace(z), negace(do)})
        return self

    def ekvivalence(self, a: str, b: str, duvod: str = "") -> "Diagram":
        """„A právě tehdy, když B" — implikace oběma směry.

        Žádný nový druh hrany. Ekvivalence JE dvojice šipek a diagram to
        nemusí umět zvlášť."""
        d = duvod or f"{a} ⇔ {b}"
        return self.implikace(a, b, d).implikace(b, a, d)

    def disjunkce(self, a: str, b: str, duvod: str = "") -> "Diagram":
        """„A nebo B" (aspoň jeden) — taky dvojice šipek: ¬A ⇒ B, ¬B ⇒ A.

        POZOR NA MEZ. Funguje to pro dva členy, protože předpoklad zůstane
        jediný výrok. U tří by musel být předpoklad součin („není A ani B
        ⇒ C") a takový uzel diagram nemá. Rozšiřovat to fingovaně by
        znamenalo tvrdit víc, než se dá odvodit — kdo potřebuje delší
        disjunkci, má sáhnout po `modely()`, které je úplné."""
        d = duvod or f"{a} ∨ {b}"
        return self.implikace(negace(a), b, d).implikace(negace(b), a, d)

    # ---- obarvení ----------------------------------------------------
    def obarvit(self, dane: Mapping) -> dict:
        """Dané hodnoty → co z nich plyne, i s odůvodněním každého kroku.

        Opakuje se, dokud něco přibývá. Není to optimalizace obcházená
        chytřejším pořadím: implikace se řetězí a nový závěr může odemknout
        šipku, kterou předchozí kolo přeskočilo.
        """
        barva: dict = {}
        proc: dict = {}
        spory: list = []

        def obarvi(uzel: str, hodnota: bool, duvod: str) -> bool:
            """Obarví uzel i jeho negaci opačně. Vrátí, jestli se něco
            změnilo; spor zapíše a barvu NEPŘEPÍŠE."""
            zmeneno = False
            for u, h in ((uzel, hodnota), (negace(uzel), not hodnota)):
                if u in barva:
                    if barva[u] != h and not any(
                            x["uzel"] == u and x["dostal"] == h for x in spory):
                        spory.append({"uzel": u, "mel": barva[u], "dostal": h,
                                      "duvod": duvod, "puvodne": proc.get(u, "")})
                else:
                    barva[u] = h
                    proc[u] = duvod
                    zmeneno = True
            return zmeneno

        for u, h in dane.items():
            obarvi(u, bool(h), "zadáno")

        zmena = True
        while zmena:
            zmena = False
            for z, do, duvod in self.sipky:
                popis = duvod or f"{z} ⇒ {do}"
                # Podmínka „a uzel ještě není obarvený" tu SCHVÁLNĚ NENÍ.
                # První verze ji měla a spolkla tím právě spor: když už uzel
                # obarvený byl, a opačně, šipka se přeskočila a rozpor se
                # nikde neprojevil. Přebarvit se stejně nedá — `obarvi()`
                # nesouhlas zapíše a hodnotu nechá být — takže opakované
                # projití nic nestojí a spor se pozná.
                if barva.get(z) is PLATI:                     # modus ponens
                    zmena |= obarvi(do, PLATI, f"{popis} · platí {z}")
                if barva.get(do) is NEPLATI:                  # modus tollens
                    zmena |= obarvi(z, NEPLATI, f"{popis} · neplatí {do}")

        return {"barva": barva, "proc": proc, "spory": spory,
                "neurceno": sorted(u for u in self.uzly if u not in barva)}

    # ---- čtení -------------------------------------------------------
    def zaver(self, obarveni: Mapping, jen_kladne: bool = True) -> list:
        """Co z toho plyne, jako věty — bez uzlů, které byly zadané.

        Vrací kladné tvrzení o každém základním výroku: buď `p`, nebo `¬p`.
        Tisknout obojí by bylo dvakrát totéž."""
        out = []
        for u, h in sorted(obarveni["barva"].items()):
            if u.startswith("¬") or (jen_kladne and not h and negace(u) in obarveni["barva"]):
                continue
            out.append({"vyrok": u if h else negace(u),
                        "plati": True,
                        "proc": obarveni["proc"].get(u if h else u, "")})
        return out


    # ---- co plyne, když není dáno nic --------------------------------
    def splnuje(self, hodnoty: Mapping) -> bool:
        """Neporušuje tohle úplné ohodnocení některou šipku?

        Implikace je nepravdivá v jediném případě — předpoklad platí
        a důsledek ne. Všechno ostatní ji splňuje, včetně toho, že
        předpoklad neplatí; proto se tu netestuje nic jiného."""
        for z, do, _ in self.sipky:
            if hodnoty.get(z) and not hodnoty.get(do):
                return False
        return True

    def modely(self, dane: Optional[Mapping] = None,
               nejvys_atomu: int = 16) -> Optional[list]:
        """Všechna bezesporná ohodnocení, nebo None při přílišné velikosti.

        PROČ TOHLE VEDLE PROPAGACE. Obarvování potřebuje první barvu:
        modus ponens i tollens vycházejí z něčeho daného. Úloha, kde není
        dáno NIC a přesto z ní něco plyne, jím projde beze změny.

            j ⇒ ¬t · k ⇒ t · ¬k ⇒ j        nic není dáno
            a přesto: někdo doma je vždycky

        Vyzkoušet všechny možnosti je metoda tabulky pravdivostních hodnot
        (Bartlová, kap. 4.1). Je ÚPLNÁ tam, kde je propagace jen rychlá:
        najde i to, co plyne až z rozboru případů.

        Cenou je 2^n, proto ten strop. Vrátit None je poctivější než počítat
        hodinu — volající se aspoň dozví, že odpověď nezná, místo aby čekal.
        """
        atomy = sorted({zaklad(u) for u in self.uzly})
        if len(atomy) > nejvys_atomu:
            return None
        dane = {zaklad(u): (bool(h) if not u.startswith("¬") else not bool(h))
                for u, h in (dane or {}).items()}
        out = []
        for maska in range(1 << len(atomy)):
            h = {a: bool(maska >> i & 1) for i, a in enumerate(atomy)}
            if any(h[a] != v for a, v in dane.items() if a in h):
                continue
            # Negace se dopočítají, aby je `splnuje` vidělo jako uzly.
            uplne = dict(h)
            uplne.update({negace(a): not v for a, v in h.items()})
            if self.splnuje(uplne):
                out.append(h)
        return out

    def plyne(self, uzel: str, dane: Optional[Mapping] = None) -> Optional[bool]:
        """Platí ten výrok ve VŠECH bezesporných ohodnoceních?

        True / False / None, a to None je plnohodnotná odpověď: znamená, že
        obojí je možné. Vrátit místo něj „ne" by z nerozhodnutelnosti
        udělalo zápor — týž prohřešek, jaký hlídá monotónní pole.

        Bez modelů se nic z toho nedá říct, takže i prázdná množina modelů
        (vstupy si odporují) vrací None, ne False."""
        m = self.modely(dane)
        if not m:
            return None
        z, kladne = zaklad(uzel), not uzel.startswith("¬")
        hodnoty = {h.get(z) for h in m}
        if len(hodnoty) > 1:
            return None
        plati = hodnoty.pop()
        return plati if kladne else (not plati)


def z_pravidel(pravidla: Iterable) -> Diagram:
    """Pravidla `term = base ∘ via` jako šipky.

    Odvozený vztah IMPLIKUJE svou složenou cestu: kde platí `tchán(a, b)`,
    platí i že vede přes otce manžela. Diagram tím dostane hrany, které se
    nikdo neučil psát — přišly z indukce nad fakty."""
    d = Diagram()
    for term, varianty in dict(pravidla).items():
        for r in varianty:
            for pres in r["via"]:
                d.implikace(f"{r['base']}∘{pres}", term,
                            f"pravidlo {term} = {r['base']} ∘ {pres}")
    return d
