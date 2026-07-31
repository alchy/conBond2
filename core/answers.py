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
from .edges import jmeno as cele_jmeno
from .language import Jazyk
from .roles import deprel
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
        self.podle_jmena = self._sestavit_jmena()

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

    def _sestavit_jmena(self) -> dict:
        """Celé jméno → věty, ve kterých stojí.

        VRSTVA OSOB POD VRSTVOU DOKUMENTŮ. `podle_entity` zná jen to, o čem
        je ČLÁNEK — devadesát jedna klíčů. Lidé zmínění uvnitř článků tam
        nejsou, a proto „Kdo je Novák?" mlčelo, ačkoli Novákové jsou
        v korpusu čtyři: nebylo co porovnat a remíza nevznikla.

        Jméno se skládá týmž pravidlem jako u hran a v grafu — jedním."""
        out: dict = defaultdict(set)
        # TVAR → CELÁ JMÉNA, ve kterých ten tvar stojí. Otázka není
        # rozebraná a píše „s Václavem Havlem"; rejstřík drží lemmata.
        # Odhadovat kmen je slepá ulička (dnes už jednou byla), ale tvary
        # v korpusu jsou — stačí si je zapamatovat.
        self.tvar_jmena: dict = defaultdict(set)
        for vi, veta in enumerate(self.vety):
            for t in veta:
                if t.get("upos") != "PROPN" or deprel(t) == "flat":
                    continue
                j = cele_jmeno(veta, t)
                if j and 2 <= len(j.split()) <= 3:
                    self.tvar_jmena[t["form"].lower()].add(j)
                    for x in veta:
                        if x.get("head") == t.get("id") and deprel(x) == "flat":
                            self.tvar_jmena[x["form"].lower()].add(j)
                # Jen celá jména — holé křestní neurčuje. A nanejvýš tři
                # slova: „Arthur Rimbaud Autor Karel Čapek" vzniklo tím, že
                # `flat` v citaci spojil, co spolu nesouvisí. Delší řetěz
                # není jméno, je to vada rozboru.
                if j and 2 <= len(j.split()) <= 3:
                    out[j].add(vi)
        # VARIANTY TÉHOŽ JMÉNA SE SLÉVAJÍ. „Karel Čapek" a „Karel Antonín
        # Čapek" je jeden člověk a doptávat se mezi nimi je nesmysl —
        # otázka by neměla odpověď, ať se vybere kterákoli.
        # Slučuje se jen JEDNOZNAČNÉ zkrácení, stejně jako u hran: kdyby
        # „Karel Novák" byl podmnožinou dvou delších jmen, nepatří ani
        # jednomu.
        slouceno = {}
        for kratke in sorted(out):
            # KDO MÁ VLASTNÍ ČLÁNEK, JE VLASTNÍ OSOBA. „Václav Havel" je
            # podmnožinou „Martin Václav Havel" a pravidlo o zkráceném
            # jménu je slilo v jednoho — jsou to ale dva lidé a odpověď
            # pak mluvila o někom jiném.
            if kratke.replace(" ", "_") in self.podle_entity:
                continue
            slova = set(kratke.split())
            delsi = [j for j in out if j != kratke and slova < set(j.split())]
            if len(delsi) == 1:
                slouceno[kratke] = delsi[0]
                out[delsi[0]] |= out.pop(kratke)
        # Tvarový rejstřík musí slučování VIDĚT. Stavěl se dřív, takže by
        # „Karel Čapek" pořád sedělo na dvě jména a otázka na vztah by
        # propadla jako nejednoznačná — ačkoli je to jeden člověk.
        for tvar, jmena in self.tvar_jmena.items():
            self.tvar_jmena[tvar] = {slouceno.get(j, j) for j in jmena}
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

    def entity_pro_jmeno(self, tvary) -> list:
        """VŠECHNY entity, které se na jméno hodí stejně dobře.

        Původní verze vracela jen tu první z nejlepších a remízu zahodila.
        Jenže remíza je informace: „Novák" sedí na Karla, Petra i Milana
        úplně stejně a vybrat jednoho znamená hádat. Doptat se je levnější
        než se splést, a hlavně je to poznat."""
        kusy = {t.lower() for t in tvary}
        skore: dict = {}
        for klic in self.podle_entity:
            casti = set(klic.split("_"))
            shoda = len(casti & kusy)
            if shoda:
                skore[klic] = shoda
        if not skore:
            return []
        nej = max(skore.values())
        return sorted(k for k, n in skore.items() if n == nej)

    def najit_entitu(self, tvary) -> str:
        """Jméno z otázky → klíč entity. Stačí, když sedí příjmení."""
        shody = self.entity_pro_jmeno(tvary)
        return shody[0] if len(shody) == 1 else (shody[0] if shody else "")

    # Kolikrát musí jméno v korpusu stát, aby se na ně vyplatilo ptát,
    # a jak výrazně musí jedna varianta převažovat, aby se ostatní daly
    # považovat za tutéž osobu.
    NEJMENE_VET = 2
    PREVAHA = 3

    def prevazujici(self, lide: list) -> list:
        """Z několika jmen ta, na která se má smysl ptát.

        REGRESE, KTERÁ TO VYNUTILA. Doptání spravilo „Kdo je Novák?" a
        rozbilo „Kdo je Ježíš?" — to se najednou ptalo mezi pěti tvary:

            ježíš krist nazaretský  134 vět
            kristus ježíš            22
            ježíš kristus            13
            ježíš duch                1     ← vada rozboru
            ježíš šimon               1     ← vada rozboru

        Jsou to varianty jednoho jména plus smetí, ne pět lidí. Pravidlo
        o zkráceném jménu je nespojilo, protože „kristus" a „krist" nejsou
        totéž slovo.

        Rozhoduje EVIDENCE, ne teorie o českých jménech. Jméno doložené
        jednou větou není osoba, na kterou se ptát; a když jedna varianta
        několikanásobně převažuje, ptá se člověk na ni. Novákové takhle
        nevypadají — 5, 3, 2, 2, 2 je vyrovnané a doptání tam zůstává."""
        vazne = [j for j in lide
                 if len(self.podle_jmena.get(j, ())) >= self.NEJMENE_VET]
        if not vazne:
            return []
        podle_vah = sorted(vazne, key=lambda j: -len(self.podle_jmena[j]))
        nej = len(self.podle_jmena[podle_vah[0]])
        druhy = len(self.podle_jmena[podle_vah[1]]) if len(podle_vah) > 1 else 0
        if druhy and nej >= self.PREVAHA * druhy:
            return [podle_vah[0]]
        return podle_vah

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

    def rozsvitit(self, text: str, tema=(), doplnit=()) -> dict:
        tvary = self.obsahove_tvary(text)
        # ODPOVĚĎ JE TAKY AKTIVACE. „Kdo je Ježíš?" → „Syn"; navazující
        # „Čí?" nemá jediné obsahové slovo, a bez doplnění by si pole
        # postavilo z celé entity a role by z něj vybrala první genitiv.
        #
        # Doplňuje se JEN u otázky, která sama nic nenese. Kdyby se slova
        # z minulého tahu přidávala vždycky, táhla by si předchozí odpověď
        # do každé další otázky — a to je zase konfabulace, jen pomalejší.
        z_odpovedi = []
        if not tvary and doplnit:
            z_odpovedi = [t for t in doplnit if self.vety_tvaru(t)]
            tvary = list(z_odpovedi)
        shody = self.entity_pro_jmeno(tvary)
        entita = shody[0] if shody else ""
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
        # NEJEDNOZNAČNÉ JMÉNO SE NEHÁDÁ. „Kdo je Novák?" sedí na Karla,
        # Petra i Milana úplně stejně; vybrat prvního znamená odpovědět
        # o někom, na koho se nikdo neptal — a nebylo by to poznat.
        #
        # Doptání se pozná od mlčení: mlčení říká „to v korpusu není",
        # doptání říká „je toho víc a vyber si". Jsou to různé odpovědi
        # a míchat je znamená zahodit informaci, kterou pole má.
        nejasne = [] if (cizi or self.sedi_cele_jmeno(jmena, entita)) \
            else [k.replace("_", " ") for k in shody if len(k.split("_")) > 1]
        # KOLIK LIDÍ SEDÍ NA JMÉNO Z OTÁZKY. Hledá se mezi OSOBAMI, ne mezi
        # dokumenty: dokumentů je devadesát jedna, lidí patnáct set.
        kusy = {j.lower() for j in jmena}
        lide = [j for j in self.podle_jmena if kusy <= set(j.split())] if kusy else []
        # ČLÁNEK PŘEBÍJÍ ZMÍNKU. „Kdy se narodil Hrabal?" nemá vyvolat
        # doptání jen proto, že se v Hrabalově článku mihne František
        # Hrabal. Korpus je o Bohumilovi; kdo má vlastní dokument, je
        # ten, na koho se lidé ptají.
        z_dokumentu = [j for j in lide if j.replace(" ", "_") in self.podle_entity]
        if len(z_dokumentu) == 1:
            lide = z_dokumentu
        lide = self.prevazujici(lide)
        if len(lide) == 1:
            # Otázka určuje jednoho člověka. Že se přitom „Karel" trefí do
            # tří dokumentů, je vedlejší — celé jméno je silnější signál
            # než shoda na půlce.
            nejasne = []
        else:
            nejasne = sorted(set(nejasne) | set(lide))[:6]
        nejasne = nejasne if len(nejasne) > 1 else []
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
                "nejasne": nejasne, "z_odpovedi": z_odpovedi,
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
    @property
    def graf(self):
        """Graf spoluvýskytů. Staví se až při první otázce na vztah —
        je to sekundy a většina rozhovorů se na vztah nezeptá."""
        if getattr(self, "_graf", None) is None:
            from .graph import Graf
            self._graf = Graf.postavit(self.vety, nejvys_vet=3, jen_osoby=True)
        return self._graf

    @property
    def zivoty(self):
        if getattr(self, "_zivoty", None) is None:
            from .cas import zivoty_z_korpusu
            self._zivoty = zivoty_z_korpusu(self.vety)
        return self._zivoty

    def spojeni(self, a: str, b: str) -> dict:
        from .graph import spojeni as _spojeni
        return _spojeni(self.graf, a, b, self.zivoty)

    def je_na_vztah(self, text: str) -> tuple:
        """Ptá se otázka na vztah dvou lidí? Vrátí je, nebo prázdno.

        Dvě jména nestačí: „Kdy se narodil Karel Čapek?" jich má taky dvě.
        Musí být i sloveso, které vztah pojmenovává — jinak by se do grafu
        posílala každá otázka se jménem a příjmením.

        Jména se hledají mezi OSOBAMI korpusu, ne mezi dokumenty; graf zná
        patnáct set lidí, dokumentů je devadesát jedna."""
        slova = {s.lower().strip("?.,") for s in text.split()}
        if not (slova & set(self.jazyk.vztahova_slovesa)):
            return ()
        # Jména se z otázky berou po DVOJICÍCH sousedních slov, protože
        # člověk píše „Bohumil Hrabal", ne „hrabal". Dvojice se hledá dřív
        # — jedno slovo sedí na víc lidí a bylo by z toho doptání.
        slovaq = [w.strip("?.,") for w in text.split()]
        jmena = [w for w in slovaq[1:] if w[:1].isupper()]
        lide = []
        for i in range(len(jmena)):
            sady = [self.tvar_jmena.get(jmena[i].lower(), set())]
            if i + 1 < len(jmena):
                sady.append(self.tvar_jmena.get(jmena[i + 1].lower(), set()))
            spolecne = set.intersection(*sady) if len(sady) > 1 and all(sady) \
                else sady[0]
            # ČLÁNEK PŘEBÍJÍ ZMÍNKU, stejně jako u doptání. „Čapek" sedí
            # na `karel čapek`, `karel antonín čapek` i `karel čapek čapek`
            # — tři varianty jednoho člověka plus vada rozboru. Vlastní
            # dokument z nich vybere toho, na koho se lidé ptají.
            if len(spolecne) > 1:
                s_clankem = [j for j in spolecne
                             if j.replace(" ", "_") in self.podle_entity]
                if len(s_clankem) == 1:
                    spolecne = set(s_clankem)
            # Nejednoznačné jméno se do grafu neposílá — vybrat prvního
            # znamená odpovídat o někom, na koho se nikdo neptal.
            if len(spolecne) == 1:
                kdo = next(iter(spolecne))
                if kdo not in lide:
                    lide.append(kdo)
        return tuple(lide[:2]) if len(lide) >= 2 else ()

    def je_na_obsah(self, text: str) -> bool:
        """Je to otázka do pole, ne do znalosti?

        Brána musí znát OBĚ cesty k odpovědi. Ptát se jen na typ znamenalo,
        že „Jako co pracoval Jirásek?" — které typ schválně nemá, aby ho
        vzala role — vypadlo z dialogu ještě před polem a odpovědělo se
        „tomuhle tvaru nerozumím". V etalonu to vidět nebylo, protože ten
        volá `odpovedet()` napřímo a bránu obchází."""
        # Brána musí znát VŠECHNY cesty k odpovědi. Když jsem přidal role,
        # ptala se jen na typ a otázka propadla ještě před polem; teď
        # přibyla třetí cesta a platí to znovu.
        return (self.jazyk.na_co_se_pta(text) is not None
                or bool(self.role_otazky(text))
                or bool(self.je_na_vztah(text)))

    def odpovedet(self, text: str, se_znalosti: bool = True, tema=(),
                  doplnit=()) -> dict:
        akt = self.rozsvitit(text, tema, doplnit)
        if akt["nejasne"]:
            return {"aktivace": dict(akt, vety=[]), "typ": None, "role": "",
                    "vet": 0, "znalost_pomohla": False, "kandidati": [],
                    "odpoved": None, "nejasne": akt["nejasne"]}
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
        # ROLE POTŘEBUJE, ČÍM ZÚŽIT. „Čí?" je samotný tázací tvar bez
        # jediného obsahového slova, takže pole zůstane celá entita
        # z tématu a role z ní vybere první genitiv, na který narazí —
        # vyšlo z toho „této noci". Je to táž nebezpečná dvojice jako
        # role v rozšířeném poli: nejslabší důkaz nad nejširším polem.
        #
        # Doplnit chybějící slova z předchozího tahu (elipsa) je vlastní
        # úloha; do té doby je mlčení správná odpověď.
        if role and not any(akt["svitici"].values()):
            role = ""
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
                "odpoved": nalezy[0]["text"] if nalezy else None,
                "nejasne": []}

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
