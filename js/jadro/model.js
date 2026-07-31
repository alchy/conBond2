/* Model: z korpusu udělá slovník, šablony a vazby.

   Rozdělení odpovědnosti mezi stranami je tohle a je záměrné:

     SLOVNÍK je SPOLEČNÝ oběma stranám a plní se z obou.
     ŠABLONY a VAZBY má každá strana vlastní.

   Že je týž tvar ve faktu i v dotazu, samo o sobě nic nespojuje — je to
   jen společný prostor tvarů. Spojení dělá až mapování, a to je jinde.

   Poloměr sdílený NENÍ: dotaz smí mít jiné r než fakt. Jde to proto, že se
   vektory obou stran nikdy neporovnávají přímo; mapování je kotvené na
   tvarech. Kdyby se párovaly vektory, musela by být r shodná. */

import { tok, stredy } from './tok.js';
import { sloty, znamenko } from './sloty.js';
import { vektor, PRAZDNY_TVAR } from './vektor.js';

export const klicTvaru = (f, punct) => (punct ? f : f.toLowerCase());

/** Prázdný sdílený slovník. */
export function slovnik() {
  return { lex: [], idx: new Map() };
}

/** Přisype do slovníku tvary jedné strany. Volá se pro obě, než se staví
    šablony — jinak by strana, která přijde druhá, neměla kam zapsat. */
export function doSlovniku(S, out, strana) {
  out.forEach((x, i) => {
    const f = x.e ? PRAZDNY_TVAR : klicTvaru(x.t.form, S.punct);
    if (!S.idx.has(f)) {
      S.idx.set(f, S.lex.length);
      S.lex.push({
        form: f, emp: !!x.e,
        rows: { f: [], q: [] },
        sents: { f: new Set(), q: new Set() },
        tids: { f: new Set(), q: new Set() },
        sady: new Map(),          // sada aktivací → kolikrát se u toho tvaru objevila
      });
    }
    const wd = S.lex[S.idx.get(f)];
    wd.rows[strana].push(i);
    wd.sents[strana].add(x.s);
    /* Sady aktivací se počítají proto, aby šlo SKLÁDAT otázku ze slovníku:
       naklikané slovo si musí odněkud přinést své aktivace. U většiny tvarů
       je sada jediná; kde jich je víc, bere se nejčastější a zbytek je
       vidět jako nejistota. */
    if (!x.e) {
      const klic = x.t.acts.slice().sort().join('|');
      const drive = wd.sady.get(klic);
      if (drive) drive.n++;
      else wd.sady.set(klic, { acts: x.t.acts.slice(), n: 1 });
    }
  });
}

/** Nejčastější sada aktivací daného tvaru, nebo null. */
export function sadaTvaru(wd) {
  if (!wd || !wd.sady || !wd.sady.size) return null;
  let nej = null;
  wd.sady.forEach(s => { if (!nej || s.n > nej.n) nej = s; });
  return nej;
}

/** Kolik různých sad tvar má — míra toho, jak jistý ten výběr je. */
export const jistotaTvaru = wd => (wd && wd.sady ? wd.sady.size : 0);

/** Šablony a vazby jedné strany. Slovník už musí být naplněný z obou. */
export function postav(vety, strana, opts, S) {
  const { r, punct, cIn, typyOn, poradi, predpona } = opts;
  const out = tok(vety, { r, punct });
  const own = stredy(out);
  const vopt = { typyOn, poradi };

  const ids = new Map(), byT = new Map(), wordOf = new Map(), sl = new Map();
  own.forEach(o => {
    const Sl = sloty(o.i, { r, cIn });
    sl.set(o.i, Sl);
    const vec = vektor(out, Sl, vopt, znamenko);
    const klic = vec.join('|');
    if (!ids.has(klic)) ids.set(klic, predpona + String(ids.size + 1).padStart(2, '0'));
    const t = ids.get(klic);
    if (!byT.has(t)) byT.set(t, { words: new Set(), rows: [], vec });
    const f = klicTvaru(o.x.t.form, punct), w = S.idx.get(f);
    byT.get(t).words.add(f);
    byT.get(t).rows.push(o.i);
    S.lex[w].tids[strana].add(t);
    wordOf.set(o.i, { w, t });
  });

  // Vazba je dvojice (slovo, šablona) — tatáž tabulka, jakou drží kód:
  // links[(w_id, t_id, zrno)] → výskyty
  const lmap = new Map();
  own.forEach(o => {
    const lk = wordOf.get(o.i), klic = lk.w + '|' + lk.t;
    if (!lmap.has(klic)) lmap.set(klic, { w: lk.w, t: lk.t, occ: [] });
    lmap.get(klic).occ.push(o.i);
  });

  return { vety, out, own, byT, wordOf, slots: sl, links: [...lmap.values()] };
}

/** Postaví obojí naráz i se společným slovníkem. Jediný vstup, který
    potřebuje zbytek programu. */
export function postavVse(data, nastaveni) {
  const poradi = nastaveni.poradi;
  const S = slovnik();
  S.punct = nastaveni.punct;
  const spolecne = { punct: nastaveni.punct, cIn: nastaveni.cIn,
                     typyOn: nastaveni.typyOn, poradi };
  const outF = tok(data.facts, { r: nastaveni.R.f, punct: nastaveni.punct });
  const outQ = tok(data.query, { r: nastaveni.R.q, punct: nastaveni.punct });
  doSlovniku(S, outF, 'f');
  doSlovniku(S, outQ, 'q');
  return {
    slovnik: S,
    f: postav(data.facts, 'f', { ...spolecne, r: nastaveni.R.f, predpona: 't' }, S),
    q: postav(data.query, 'q', { ...spolecne, r: nastaveni.R.q, predpona: 'q' }, S),
  };
}
