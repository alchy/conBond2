"""Odpověď na otázku o obsahu korpusu — a hlavně: CO SE AKTIVUJE.

Ne vyhledávání v textu. Otázka se rozloží a každý kus se hledá tím kanálem,
kterým se v poli chová:

    OSOBA je AKTIVACE. Ve 169 ze 170 zlatých vět jméno z otázky VŮBEC NENÍ —
    čeština podmět zahazuje („Narodil se na brněnském předměstí Židenice…")
    a identita sedí jako `Ent=bohumil_hrabal`, kterou doplnila koreference.
    Hledání podle tvaru dalo 1 %, přes aktivaci 100 %.

    SLOVESO je TVAR a najde se ve společném slovníku, který řekne, ve kterých
    větách faktů svítí.

Průnik obojího je POLE ODPOVĚDI; tázací tvar řekne, jaký druh místa v něm
hledat, a agenti Chronos a Topos ta místa označili předem.

DVA STUPNĚ, PROTOŽE JINAK SE TRESTÁ ZÁMĚR. Šablona neidentifikuje jednu
odpověď, ale DRUH místa, kde odpověď leží — „Kde se narodil X?" má trefit
rodiště u všech autorů naráz. Vybrat z pole tu jednu je úloha pro identitu,
ne pro pole, a proto se měří zvlášť.

ZNALOST SE ČTE AŽ TADY, ne v datech. Otázka smí zobecňovat: kdo se ptá na
spisovatele, míří i na Hrabala, protože `hrabal ∈ spisovatel`. Fakt
zobecňovat nesmí — kdyby se expandovalo do dat, vektor se prodlouží a
sdílení podle měření KLESNE.
"""

from collections import defaultdict
from typing import Optional

from .field import Pole
from .language import Jazyk
from .roles import Role
from .tvrzeni import Znalost


class Odpovidac:
    """Otázka dovnitř, aktivace a kandidáti ven."""

    def __init__(self, pole: Pole, znalost: Optional[Znalost] = None,
                 jazyk: Optional[Jazyk] = None):
        self.pole = pole
        self.znalost = znalost or Znalost()
        self.jazyk = jazyk or Jazyk.nacist()
        self.role = Role(self.jazyk)
        self.slovnik = pole.ziskat_slovnik()
        self.vety = pole.uloziste.nacist_korpus("facts")
        self.podle_typu = self._sestavit_navesky()
        self.podle_entity = self._sestavit_entity()

    # ---- rejstříky ---------------------------------------------------
    def _sestavit_navesky(self) -> dict:
        """Věta → typ → rozsahy, které agenti označili.

        Životní rozpětí v závorce se vynechá: „oženil se s Marií Podhajskou
        ( 1859 – 1927 )" nese čas, ale je to rok narození JEHO ŽENY, ne
        odpověď na otázku po ději. Agent Bio to označí `Udal=zivot` právě
        proto, že u nedefiniční závorky nevíme, čí život to je."""
        out: dict = defaultdict(lambda: defaultdict(list))
        # `komu` u jmenného přísudku: ve větě jich může být víc a jen jeden
        # patří tomu, na koho se ptáme. Drží se stranou od rozsahů, aby
        # zbytek kódu zůstal stejný.
        self.komu: dict = {}
        for vi, veta in enumerate(self.vety):
            for t in veta:
                if any(a == "Udal=zivot" for a in t["acts"]):
                    continue
                for n in t.get("navesky", ()):
                    out[vi][n["typ"]].append(tuple(n["rozsah"]))
                    h = n.get("hodnota")
                    if isinstance(h, dict) and h.get("komu"):
                        self.komu[(vi, tuple(n["rozsah"]))] = h["komu"]
        return out

    def _sestavit_entity(self) -> dict:
        """Entita → věty, ve kterých o ní je řeč. Klíč je z `Ent=`, protože
        jméno v té větě obvykle nestojí."""
        out: dict = defaultdict(set)
        for vi, veta in enumerate(self.vety):
            for t in veta:
                for a in t["acts"]:
                    if a.startswith("Ent="):
                        out[a[4:]].add(vi)
        return out

    # ---- aktivace ----------------------------------------------------
    def obsahove_tvary(self, text: str) -> list:
        kusy = text.replace("?", " ").replace(".", " ").replace(",", " ").split()
        return [k.lower() for k in kusy if not self.jazyk.je_prazdne(k.lower())]

    def vety_tvaru(self, tvar: str) -> set:
        p = self.slovnik.najit(tvar)
        return set(p.vety["f"]) if p else set()

    def najit_entitu(self, tvary) -> str:
        """Jméno z otázky → klíč entity. Stačí, když sedí příjmení."""
        kusy = {t.lower() for t in tvary}
        nejlepsi, skore = "", 0
        for klic in self.podle_entity:
            shoda = len(set(klic.split("_")) & kusy)
            if shoda > skore:
                nejlepsi, skore = klic, shoda
        return nejlepsi

    def sedi_cele_jmeno(self, jmena, entita: str) -> bool:
        """Sedí VŠECHNA jména z otázky na jednu entitu?

        „Marie Curie" trefila `marie_majerová` přes křestní jméno a systém
        pak odpověděl rokem úmrtí Majerové. Shoda na jednom kuse jména
        nestačí — je to táž past jako „Karel patřil všem sedmadvaceti
        Karlům", jen na vstupu místo na výstupu."""
        if not entita:
            return False
        casti = set(entita.split("_"))
        return all(j.lower() in casti for j in jmena)

    @staticmethod
    def jmena_v_otazce(text: str) -> list:
        """Slova s velkým písmenem uprostřed otázky. V češtině je to slušné
        vodítko na vlastní jméno a první slovo se vynechá, protože tam velké
        písmeno nese začátek věty, ne jméno."""
        kusy = text.replace("?", " ").replace(".", " ").split()
        return [k for k in kusy[1:] if k[:1].isupper()]

    def rozsvitit(self, text: str, tema=()) -> dict:
        tvary = self.obsahove_tvary(text)
        entita = self.najit_entitu(tvary)
        # TÉMA DRŽÍ ŘETĚZ. „Kdo je Hrabal?" a pak „Kde se narodil?" — druhá
        # otázka jméno nemá a bez tématu se pole složí ze samotného slovesa;
        # měřeno, že pak odpoví pokaždé týmž místem bez ohledu na to, o kom
        # byla řeč.
        #
        # Téma se bere JEN u otázky, která žádné jméno nezmiňuje. Kdyby
        # doplňovalo i tam, kde jméno je, zachránilo by „Kdy se narodil
        # Sherlock Holmes?" tématem předchozí osoby — a z paměti tématu by
        # se stala nová cesta ke konfabulaci.
        z_tematu = ""
        if not entita and not self.jmena_v_otazce(text):
            z_tematu = next((e for e in tema if e in self.podle_entity), "")
            entita = z_tematu
        vety_entity = set(self.podle_entity.get(entita, ()))
        # JMÉNO, KTERÉ V KORPUSU VŮBEC NENÍ, ZNAMENÁ „NEVÍM". Bez tohohle
        # řezu odpověděl systém na „Kdy se narodil Sherlock Holmes?" datem
        # někoho jiného: pole se složilo ze samotného slovesa „narodil" a to
        # svítí u půlky korpusu.
        #
        # Testuje se VÝSKYT V KORPUSU, ne shoda s entitou. První verze
        # odmítala všechno, co není jedním z 49 životopisů — tedy i „Ol
        # Doinyo Lengai" a „Ježíš", o kterých korpus mluví celé kapitoly.
        # Entit je pár desítek, kdežto jmen v textu tisíce.
        jmena = self.jmena_v_otazce(text)
        cizi = bool(jmena) and not self.sedi_cele_jmeno(jmena, entita) \
            and any(not self.vety_tvaru(j.lower()) for j in jmena)
        zbytek = [t for t in tvary if t not in set(entita.split("_"))]
        kde = {t: self.vety_tvaru(t) for t in zbytek}
        zname = {t: v for t, v in kde.items() if v}

        # POLE SE VÁŽÍ, NEPRONÍKÁ. Průnik VŠECH obsahových slov je křehký:
        # „Kam odešel Ježíš s matkou a učedníky?" má čtyři slova, každé svítí
        # ve stovkách vět, a průnik všech čtyř je prázdný — přitom taková
        # věta v korpusu je. A u „Kde leží sopka Ol Doinyo Lengai?" naopak
        # entita článku (sopka) převálcovala konkrétní jméno.
        #
        # Vážení dělá obojí správně: věta dostane bod za každé slovo otázky,
        # které v ní stojí, a bod navíc za entitu. Berou se věty s nejvyšším
        # skóre — tedy ty, které z otázky pokrývají nejvíc.
        skore: dict = defaultdict(int)
        for vety_slova in zname.values():
            for vi in vety_slova:
                skore[vi] += 1
        for vi in vety_entity:
            skore[vi] += 1
        signalu = len(zname) + (1 if vety_entity else 0)
        siroko = False
        prunik = set()
        if skore:
            nej = max(skore.values())
            # KDYŽ SE ŽÁDNÉ DVA SIGNÁLY NEPOTKAJÍ, JE TO „NEVÍM". Jinak by
            # z vážení vzniklo SJEDNOCENÍ místo zúžení: „Kdy se narodil pes
            # domácí?" má entitu (76 vět) i sloveso (67 vět), nikde se
            # nesejdou, a bez tohohle řezu se pole složilo ze všech 143 —
            # a odpovědělo datem narození Hrabalova bratra.
            if signalu >= 2 and nej < 2:
                prunik = set()
            else:
                prunik = {vi for vi, n in skore.items() if n == nej}
                # Nižší skóre než součet všech signálů znamená, že se něco
                # z otázky v jedné větě nepotkalo — pole je širší, než jsme
                # chtěli, a je poctivé to říct.
                siroko = nej < signalu
        if cizi:
            prunik, siroko = set(), False
        return {"tvary": tvary, "entita": entita, "vet_entity": len(vety_entity),
                "svitici": {t: len(v) for t, v in kde.items()},
                "nezname": [t for t, v in kde.items() if not v],
                "jmena": jmena, "cizi_jmeno": cizi, "z_tematu": bool(z_tematu),
                "siroko": siroko, "vety": prunik}

    def rozsirit(self, tvar: str) -> set:
        """Věty, které tvar zasáhne PŘES ZNALOST. Potomek se hledá napřed
        jako entita a teprve pak jako tvar — jinak by expanze našla jen věty,
        kde jméno doopravdy stojí, což je u pro-dropu zlomek."""
        vety = set()
        for potomek in self.znalost.potomci(tvar.lower()):
            klic = self.najit_entitu(potomek.split())
            if klic:
                vety |= self.podle_entity[klic]
            else:
                for kus in potomek.split():
                    vety |= self.vety_tvaru(kus)
        return vety

    # ---- odpověď -----------------------------------------------------
    def je_na_obsah(self, text: str) -> bool:
        """Je to otázka do pole, ne do znalosti?

        Brána musí znát OBĚ cesty k odpovědi. Ptát se jen na typ znamenalo,
        že „Jako co pracoval Jirásek?" — které typ schválně nemá, aby ho
        vzala role — vypadlo z dialogu ještě před polem a odpovědělo se
        „tomuhle tvaru nerozumím". V etalonu to vidět nebylo, protože ten
        volá `odpovedet()` napřímo a bránu obchází."""
        return (self.jazyk.na_co_se_pta(text) is not None
                or bool(self.role_otazky(text)))

    def odpovedet(self, text: str, se_znalosti: bool = True, tema=()) -> dict:
        akt = self.rozsvitit(text, tema)
        vety = set(akt["vety"])
        pomohla = set()
        if se_znalosti:
            for t in akt["tvary"]:
                pomohla |= self.rozsirit(t)
            if pomohla:
                vety = pomohla if not vety else ((vety & pomohla) or vety)
        typ = self.jazyk.na_co_se_pta(text)
        o_kom = akt["tvary"] if typ == "Typ=druh" else ()
        nalezy = self.sebrat(vety, typ, o_kom)
        # ROLE JAKO ZÁCHRANNÁ SÍŤ. Typ našel agent a je přesnější — „v Praze"
        # ověřil Topos jako místo. Kde agent mlčí (Komu, Čím, Proč, Jak),
        # rozhodne větný člen z rozboru: „Řekl JIM" je `obl` v dativu a leží
        # to v datech, jen se na to nikdo nedíval.
        # …ALE JEN TAM, KDE AGENT VŮBEC NENÍ. Když se ptáme „Kde",
        # odpovídá Topos, a jeho mlčení je ODPOVĚĎ: v poli žádné místo není.
        # Přebít ho rolí `kde` znamená vzít první lokál, který se namane —
        # „Kde se narodil Franz Kafka?" tak vyrobilo „ve svých prózách".
        # Role proto smí mluvit jen u otázek, které žádný typ nepokrývá:
        # Komu, Čím, Proč, Jak. Prázdný `typ` je ta podmínka.
        role = "" if typ else self.role_otazky(text)
        if not nalezy and role:
            nalezy = self.sebrat_roli(vety, role)
        # ZÚŽENÍ, KTERÉ NIC NENAJDE, JE HORŠÍ NEŽ ŠIRŠÍ POLE — ale jen když
        # otázce rozumíme celé. „Kdy se narodil Alois Jirásek?" protnulo
        # entitu se slovesem na jedinou větu, a ta žádný čas neměla: rok
        # narození stojí v úvodní závorce, kde slovo „narodil" není. Tam se
        # rozšířit vyplatí.
        #
        # NEROZŠIŘOVAT, když otázka obsahuje slovo, které korpus nezná
        # („Kolik měl Hrabal LETADEL?"), nebo cizí jméno. Tam by z „nevím"
        # vzniklo „tady máš něco o té osobě" — a to je zase vymýšlení, jen
        # opatrnější. První verze tohohle řezu neměla a rozbila dva zápory.
        lze_rozsirit = (akt["vet_entity"] and not akt["cizi_jmeno"]
                        and not akt["nezname"])
        if not nalezy and lze_rozsirit:
            sirsi = set(self.podle_entity.get(akt["entita"], ()))
            # Role se do širšího pole nepouští. Rozšíření zahazuje právě
            # to, čím se otázka lišila — „S kým se OŽENIL Hrabal" se
            # v korpusu nepotká ani jednou, a v širším poli má role
            # `s_kym_cim` na výběr ze všech jeho společníků. Typ přežije,
            # protože ho ověřil agent: datum je datum i po rozšíření.
            # Role ověřená není, takže mlčí.
            nalezy = self.sebrat(sirsi, typ, o_kom)
            if nalezy:
                vety, akt["siroko"] = sirsi, True
        # Množiny se ven neposílají — nález jde rovnou do JSON pro prohlížeč.
        ven = dict(akt, vety=sorted(akt["vety"])[:200])
        return {"aktivace": ven, "typ": typ, "role": role, "vet": len(vety),
                "znalost_pomohla": bool(pomohla), "kandidati": nalezy,
                "odpoved": nalezy[0]["text"] if nalezy else None}

    def sebrat(self, vety, typ, o_kom=()) -> list:
        """Úseky daného druhu ve větách pole.

        U `Typ=druh` rozhoduje ještě `o_kom`: věta „Kdo je lhář, ne-li ten,
        kdo popírá, že Ježíš je Kristus?" má jmenné přísudky dva a jen jeden
        patří Ježíšovi. Kdo se ptá na osobu, dostane jen její přísudky —
        a když žádný nesedí, radši nic než cizí."""
        kusy = {k.lower() for k in o_kom}
        out, jine = [], []
        for vi in sorted(vety):
            for rozsah in self.podle_typu.get(vi, {}).get(typ, ()):
                zaznam = {"veta": vi, "rozsah": list(rozsah),
                          "text": self.text_rozsahu(vi, rozsah),
                          "kontext": self.text_vety(vi)}
                komu = self.komu.get((vi, tuple(rozsah)))
                if kusy and komu and kusy & set(komu.split()):
                    out.append(zaznam)
                else:
                    jine.append(zaznam)
        return out if (kusy and out) else (jine if not kusy else out)

    def role_otazky(self, text: str) -> str:
        """Role, kterou má mít odpověď. Přísudek ji smí přemapovat —
        u pojmenování se ptáme „jak", ale odpovědí je jméno.

        Sloveso otázky se hledá podle kmene, protože otázka není rozebraná:
        „jmenovaly" a „jmenovat" mají společných šest písmen. Je to zkratka,
        ne rozbor — kdyby se ukázala jako těsná, patří sem UDPipe."""
        prisudek = ""
        for t in self.obsahove_tvary(text):
            for klic in self.jazyk.role_podle_prisudku:
                if t[:6] and klic.startswith(t[:6]):
                    prisudek = klic
                    break
        return self.role.role_otazky(text, prisudek)

    def sebrat_roli(self, vety, role: str) -> list:
        """Úseky dané role. Role se počítá až tady, nad větami POLE — ne
        dopředu nad celým korpusem: pole má desítky vět, korpus 25 755,
        a rejstřík rolí by stál víc paměti než celé pole."""
        out = []
        for vi in sorted(vety):
            veta = self.vety[vi]
            for i in self.role.role_vety(veta).get(role, ()):
                r = self.role.rozsah(veta, i)
                out.append({"veta": vi, "rozsah": r,
                            "text": self.text_rozsahu(vi, r),
                            "kontext": self.text_vety(vi)})
        return out

    # ---- čtení -------------------------------------------------------
    def text_rozsahu(self, vi: int, rozsah) -> str:
        veta = self.vety[vi]
        return " ".join(veta[j]["form"] for j in rozsah if j < len(veta))

    def text_vety(self, vi: int) -> str:
        return " ".join(t["form"] for t in self.vety[vi]) \
            .replace(" .", ".").replace(" ,", ",")
