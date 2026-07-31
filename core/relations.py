"""Vztahy jako skládání — definiční věta je DATA, ne tabulka v kódu.

CO TO ŘEŠÍ. „Kdo je Petrův tchán?" nejde odpovědět, dokud někdo nenapíše,
co tchán je. Přitom to v korpusu stojí obyčejnou větou:

    Tchán je otec manžela nebo manželky.

Z ní se dá odvodit pravidlo `tchán = otec ∘ (manžel | manželka)` a tím se
z primitivních hran (otec, matka, manžel…) dopočítají odvozené. Runtime pak
nemá o vztazích jedinou větev navíc — odvozená hrana je obyčejný fakt.

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
