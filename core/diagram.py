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
