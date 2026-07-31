"""Vztahy jako skládání — definiční věta je DATA, ne tabulka v kódu.

CO TO ŘEŠÍ. „Kdo je Petrův tchán?" nejde odpovědět, dokud se neví, co tchán
je. Pravidlo `tchán = otec ∘ (manžel | manželka)` se dá získat DVĚMA cestami
a ta druhá je ta podstatná.

    1. Z DEFINICE          „Tchán je otec manžela nebo manželky."
    2. ZE VZTAHU MEZI FAKTY   korpus říká  tchán(Karel, Jana)
                              a jinde      otec(Karel, Petr)
                                           manžel(Petr, Jana)

První cesta je pohodlná, ale spoléhá na to, že text definici obsahuje —
a životopis, evangelium ani článek o včelách žádné definice nepíšou.

Druhá se učí z faktů samotných: pravidlo NENÍ v žádné větě, je vidět až
ve VZTAHU MEZI VĚTAMI. Kde se složená cesta opakovaně kryje s doloženou
hranou, je to pravidlo — a čím víc dokladů, tím jistější.

Obojí končí stejně: z primitivních hran se dopočítají odvozené a runtime
nemá o vztazích jedinou větev navíc — odvozená hrana je obyčejný fakt.

A TÍM SE VRSTVA ZAVŘE SAMA NA SEBE. Odvozená hrana je vstup dalšího
odvozování i dalšího UČENÍ: z faktů vzniknou pravidla, z pravidel nové
fakty, a nad těmi se dají hledat pravidla znova. Získávání faktů z textu
tak přestává být jednosměrné.

Ověřeno na vymyšlené rodině, kde není jediná definiční věta:

    matka = manželka ∘ otec     doklad 2 · spor 0 · pokrytí 100 %
      ⟹ matka(Věra, Lucie)      hrana, která v textu NIKDE NESTOJÍ

Text říká, že Věra je manželka Karla a Karel otec Lucie. Že je Věra matka
Lucie, neříká nikde — a přesto to plyne.

PŘEVZATO Z conBondu (`reldefs.py`). Tam to bylo popsané jako mapování jedné
faktické vrstvy na druhou; podstatné je, že se pravidla NEPÍŠOU, nýbrž ČTOU
z textu. Definiční text je obyčejný dokument v `data/raw/`.

    Tchán je otec manžela nebo manželky.
      │      │        └── nmod Gen ──┴── conj      → via
      │      └── root NOUN se sponou                → base
      └── nsubj NOUN                                → term

DVA ROZSAHY PLATNOSTI. Pravidlo, které se uzavře čistě nad JAZYKOVÝMI vztahy
(otec, matka, syn…), platí nad každým textem — definuje jazyk, ne obsah.
Pravidlo, které potřebuje slovní zásobu svého dokumentu, platí jen tam.
Rozdíl je podstatný: „děd je otec otce" platí vždycky, kdežto co znamená
„vedoucí katedry", záleží na tom, o čem ten text je.

FIXPOINT, PROTOŽE DEFINICE STOJÍ NA DEFINICÍCH. „Praděd je otec děda"
nedává smysl, dokud není přijat „děd". Přijatý term rozšíří slovník a kolo
se opakuje, dokud něco přibývá.

CHYBĚJÍCÍ HRANA NENÍ PROTIPŘÍKLAD. Pole je monotónní: co v něm není, o tom
se nikdo neptal — ne že to neplatí. Když tedy složená cesta dá hranu, kterou
korpus nedokládá, NENÍ to spor, jen nedoložený případ. Sporem je až doložená
hrana, která tvrdí něco jiného, a to jen u vztahů, které mají jediné řešení
(jeden otec, ne jeden bratr).

Bez tohohle rozlišení by každé pravidlo vyšlo jako chybné, protože žádný
korpus není úplný.
"""

from typing import Iterable, Mapping, Optional, Sequence

from .roles import deprel, pad


def lemma(token: Mapping) -> str:
    return (token.get("lemma") or token.get("form") or "").lower()


def pravidla_z_vety(veta: Sequence[Mapping],
                    slovnik: Optional[set] = None) -> list:
    """Definiční věta → [(term, base, [via…])], nebo prázdno.

    Bere se JEN kopulová věta se jmenným přísudkem — „Tchán JE otec…".
    Věta bez spony nic nedefinuje, jen vypráví.

    `slovnik` je síto: pravidlo se přijme, jen když base i všechna via
    slovník už zná. S `None` se jen sbírají kandidáti a filtruje se až
    ve fixpointu, protože pořadí vět v textu nemá o platnosti rozhodovat.
    """
    if not any("cop" in t["acts"] for t in veta):
        return []
    koren = next((t for t in veta
                  if deprel(t) == "root" and t.get("upos") == "NOUN"), None)
    if koren is None:
        return []
    kid = koren.get("id")
    # Term musí být OBECNÉ jméno. „Karel je otec Petra" je fakt o Karlovi,
    # ne definice slova — vlastní jméno (PROPN) definici nedává.
    term = next((lemma(t) for t in veta if t.get("head") == kid
                 and deprel(t) == "nsubj" and t.get("upos") == "NOUN"), "")
    if not term:
        return []
    via = []
    for t in veta:
        if t.get("head") != kid or t.get("upos") != "NOUN":
            continue
        if deprel(t) not in ("nmod", "nmod:poss") or pad(t) != "Gen":
            continue
        via.append(lemma(t))
        # „manžela NEBO manželky" — druhá možnost visí na první přes `conj`
        # a je to plnohodnotná cesta, ne upřesnění.
        for x in veta:
            if x.get("head") == t.get("id") and deprel(x) == "conj" \
                    and x.get("upos") == "NOUN":
                via.append(lemma(x))
    via = sorted(set(via))
    if not via:
        return []
    base = lemma(koren)
    if slovnik is not None and (base not in slovnik
                                or any(v not in slovnik for v in via)):
        return []
    return [(term, base, via)]


def fixpoint(kandidati: Iterable, zakladni: Iterable,
             predikaty_dokumentu: Optional[dict] = None) -> dict:
    """Kandidáti → přijatá pravidla, ve dvou kolech podle rozsahu platnosti.

    `kandidati` jsou čtveřice (term, base, [via…], dokument).
    Vrací {term: [{"base", "via", "rozsah", "dok"}]}.

    Nejdřív se uzavře JAZYKOVÁ vrstva — co stojí jen na základních vztazích,
    platí všude a rovnou rozšiřuje slovník pro další kolo. Teprve pak se
    zkoušejí pravidla, která potřebují slovní zásobu svého dokumentu; ta
    zůstanou svázaná s ním.

    Pořadí je podstatné: kdyby se dokumentová kola pouštěla první, stal by
    se z náhodného textu zdroj univerzálních definic.
    """
    jazyk = set(zakladni)
    predikaty_dokumentu = predikaty_dokumentu or {}
    prijata: dict = {}

    def uz_je(term, base, via):
        return any(r["base"] == base and r["via"] == via
                   for r in prijata.get(term, ()))

    def kolo(vybrat_slovnik, rozsah):
        zmena = True
        while zmena:
            zmena = False
            for term, base, via, dok in kandidati:
                if uz_je(term, base, via):
                    continue
                slovnik = vybrat_slovnik(dok)
                if base in slovnik and all(v in slovnik for v in via):
                    prijata.setdefault(term, []).append(
                        {"base": base, "via": via, "rozsah": rozsah,
                         "dok": None if rozsah == "jazyk" else dok})
                    if rozsah == "jazyk":
                        jazyk.add(term)
                    else:
                        dokumentove.setdefault(dok, set()).add(term)
                    zmena = True

    dokumentove: dict = {}
    kolo(lambda dok: jazyk, "jazyk")
    kolo(lambda dok: jazyk | dokumentove.get(dok, set())
         | set(predikaty_dokumentu.get(dok, ())), "dokument")
    return prijata


def odvodit_hrany(hrany: Iterable, pravidla: Mapping, kol: int = 6) -> list:
    """Primitivní hrany + pravidla → NOVÉ hrany.

    Hrana je (predikát, kdo, čí) — „otec(Karel, Petr)" znamená, že Karel je
    otec Petra. Pravidlo `term = base ∘ via` skládá dvě hrany za sebou:

        otec(Karel, Petr) ∧ manžel(Petr, Jana)  ⟹  tchán(Karel, Jana)

    Opakuje se, dokud něco přibývá — odvozená hrana smí být vstupem další
    kompozice. `kol` je pojistka proti cyklu v pravidlech, ne parametr
    k ladění: text si může protiřečit a smyčka na to nesmí doplatit.
    """
    znamé = {(p, k, c) for p, k, c in hrany}
    nove: list = []
    for _ in range(kol):
        pribylo = False
        podle_predikatu: dict = {}
        for p, k, c in znamé:
            podle_predikatu.setdefault(p, []).append((k, c))
        for term, varianty in pravidla.items():
            for r in varianty:
                for k1, c1 in podle_predikatu.get(r["base"], ()):
                    for pres in r["via"]:
                        for k2, c2 in podle_predikatu.get(pres, ()):
                            if c1 != k2:
                                continue
                            h = (term, k1, c2)
                            if h in znamé:
                                continue
                            znamé.add(h)
                            nove.append({"predikat": term, "kdo": k1,
                                         "ci": c2, "pres": [r["base"], pres],
                                         "odvozeno": True})
                            pribylo = True
        if not pribylo:
            break
    return nove


# ---- učení pravidel ze samotných faktů ---------------------------------

def slozit_cestu(podle_predikatu: Mapping, base: str, pres: str) -> set:
    """Hrany, které vzniknou složením dvou predikátů za sebou.

    base(a, b) ∧ pres(b, c) ⟹ (a, c). Prostřední článek se zahazuje —
    zajímá nás, co cesta spojuje, ne kudy vedla."""
    prostredni: dict = {}
    for k, c in podle_predikatu.get(pres, ()):
        prostredni.setdefault(k, []).append(c)
    return {(k1, c2) for k1, c1 in podle_predikatu.get(base, ())
            for c2 in prostredni.get(c1, ())}


def navrhnout_pravidla(hrany: Iterable, jedinecne: Iterable = (),
                       min_dokladu: int = 2) -> list:
    """Hrany korpusu → pravidla, která z nich VYPLÝVAJÍ. Žádná definice.

    Pro každý predikát se zkusí každá dvojice (base, přes) a spočítá se, jak
    se složená cesta kryje s tím, co korpus o tom predikátu doopravdy říká.

        tchán(Karel, Jana)  doloženo
        otec(Karel, Petr) ∧ manžel(Petr, Jana)  ⟹  (Karel, Jana)  ✓ kryje se

    TŘI ČÍSLA, NE JEDNO SKÓRE. Každé odpovídá na jinou otázku a slévat je
    znamená zahodit rozdíl mezi „málo dokladů" a „doloženo špatně":

        doklad   složená cesta trefila doloženou hranu
        navic    cesta dala hranu, kterou korpus nedokládá
        spor     cesta si odporuje s doloženou hranou

    `navic` NENÍ chyba. Pole je monotónní: chybějící hrana znamená, že se
    nikdo neptal. Právě proto se počítá zvlášť a do rozhodování nevstupuje —
    kdyby vstupovala, každé pravidlo by nad neúplným korpusem propadlo.

    Spor je vidět jen u vztahů z `jedinecne` — těch, které mají jediné
    řešení. Otce má člověk jednoho, takže dvě různá tvrzení jsou spor;
    bratrů může mít pět a druhý bratr nevyvrací prvního.

    Vrací seznam seřazený od nejlépe doloženého; nic nepřijímá ani
    nezavrhuje. Rozhodnutí patří tomu, kdo vidí i práh — pravidlo se dvěma
    doklady je něco jiného než pravidlo s dvěma sty.
    """
    podle_predikatu: dict = {}
    for p, k, c in hrany:
        podle_predikatu.setdefault(p, []).append((k, c))
    jedinecne = set(jedinecne)
    predikaty = sorted(podle_predikatu)
    out = []
    for term in predikaty:
        doloz = set(podle_predikatu[term])
        # Jedinečnost sedí na DRUHÉM konci hrany, ne na prvním. `matka(Věra,
        # Petr)` znamená „Věra je matka Petra": jedno dítě má jednu matku,
        # kdežto jedna matka může mít dětí kolik chce. Kdo to otočí, dostane
        # spor pokaždé, když má rodič druhé dítě — a to není spor, to je
        # rodina.
        podle_ciho: dict = {}
        for k, c in doloz:
            podle_ciho.setdefault(c, set()).add(k)
        for base in predikaty:
            if base == term:
                continue
            for pres in predikaty:
                # `base ∘ term` by dokazovalo term sebou samým.
                if pres == term:
                    continue
                cesta = slozit_cestu(podle_predikatu, base, pres)
                if not cesta:
                    continue
                doklad = cesta & doloz
                if len(doklad) < min_dokladu:
                    continue
                navic = cesta - doloz
                # Spor je, až když korpus o TÉMŽE druhém konci tvrdí něco
                # jiného. Že o něm nemluví vůbec, spor není — pole je
                # monotónní.
                spor = {(k, c) for k, c in navic if term in jedinecne
                        and podle_ciho.get(c) and k not in podle_ciho[c]}
                out.append({"term": term, "base": base, "via": [pres],
                            "doklad": len(doklad), "navic": len(navic) - len(spor),
                            "spor": len(spor),
                            "pokryti": len(doklad) / len(doloz)})
    out.sort(key=lambda r: (-r["doklad"], r["spor"], r["term"]))
    return out
