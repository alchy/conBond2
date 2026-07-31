/* Jediné místo, kde se model z backendu překlopí do tvaru, se kterým se
   kreslí. Prohlížeč nic nepočítá — zdroj pravdy sedí v Pythonu (core/).

   Adaptér je tu schválně: kdyby si každý list překládal odpověď sám,
   rozlezl by se tvar dat po celém frontendu a změna v jádře by se musela
   dohledávat na deseti místech. */

export const PRAZDNO = '∅';
export const PRAZDNY_TVAR = '<empty>';
/* Autorita nad těmihle značkami je core/sources.py; tady jsou jen proto,
   aby se s nimi dalo kreslit bez dotazu na server. */

export const znamenko = d => (d > 0 ? '+' + d : '' + d);

/** Řádky pole: ze serveru přijde rozvržení, tokeny doplní korpus. */
function radky(rozvrzeni, vety, syrove) {
  return rozvrzeni.map(([s, k]) => {
    if (k === null) return { e: true, s };
    const veta = vety[s] || [];
    const tokeny = syrove ? veta : veta.filter(t => t.upos !== 'PUNCT');
    return { t: tokeny[k], s, k };
  });
}

function sablony(zeServeru) {
  const m = new Map();
  Object.entries(zeServeru).forEach(([t, info]) => {
    m.set(t, { vec: info.vec, delka: info.delka,
      words: new Set(info.tvary), rows: info.radky });
  });
  return m;
}

function strana(zeServeru, vety, syrove) {
  const out = radky(zeServeru.radky, vety, syrove);
  const own = out.map((x, i) => ({ x, i })).filter(o => !o.x.e);
  const slots = new Map();
  Object.entries(zeServeru.sloty).forEach(([i, sl]) => {
    slots.set(+i, sl.map(([j, d]) => ({ j, d })));
  });
  const links = zeServeru.vazby.map(v => ({ w: v.w, t: v.t, occ: v.vyskyty }));
  const wordOf = new Map();
  links.forEach(L => L.occ.forEach(i => wordOf.set(i, { w: L.w, t: L.t })));
  return { vety, out, own, byT: sablony(zeServeru.sablony), wordOf, slots, links,
    cisla: zeServeru.cisla };
}

function slovnik(zeServeru) {
  const lex = zeServeru.map(p => ({
    form: p.tvar, emp: p.prazdny,
    rows: p.radky,
    sents: { f: new Set(p.vety.f), q: new Set(p.vety.q) },
    tids: { f: new Set(p.sablony.f), q: new Set(p.sablony.q) },
    jistota: p.jistota,
  }));
  const idx = new Map();
  lex.forEach((w, i) => idx.set(w.form, i));
  return { lex, idx };
}

/** Odpověď /api/field → model pro kreslení. */
export function prevzit(odpoved, korpusy) {
  const syrove = !!odpoved.nastaveni.syrove;
  return {
    nastaveni: odpoved.nastaveni,
    klicMapovani: odpoved.klic_mapovani,
    slovnik: slovnik(odpoved.slovnik),
    f: strana(odpoved.f, korpusy.facts, syrove),
    q: strana(odpoved.q, korpusy.query, syrove),
  };
}
