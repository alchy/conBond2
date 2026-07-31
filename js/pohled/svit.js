/* Zvýrazňování a připínání.

   Plátno je široké přes tři tisíce pixelů, takže samotný hover nestačí —
   než přejedeš očima z jednoho konce na druhý, zhasne. Klik proto PŘIPNE
   a drží, dokud neklikneš jinam.

   Zvýraznění je PRŮCHOZÍ celým řetězem: ať sáhneš kamkoli, dojede to na
   oba konce — od řádku v poli až k šabloně a zpátky. */

import { stav } from '../stav.js';
import { znamenko } from '../jadro/sloty.js';
import { PRAZDNY_TVAR } from '../jadro/vektor.js';

export function zhasni(v) {
  v.sv.querySelectorAll('path').forEach(p => p.classList.remove('hot'));
  v.root.querySelectorAll('li.hot,.line.hot,.line.slot')
    .forEach(e => e.classList.remove('hot', 'slot'));
  v.root.querySelectorAll('.pinned').forEach(e => e.classList.remove('pinned'));
  v.rows.querySelectorAll('.gut').forEach(g => {
    if (g.dataset.orig !== undefined) { g.textContent = g.dataset.orig; delete g.dataset.orig; }
  });
}

const maluj = (v, pred) => v.sv.querySelectorAll('path').forEach(p => {
  p.classList.remove('hot'); if (pred(p.dataset)) p.classList.add('hot');
});
const znac = (v, sel) => v.root.querySelectorAll(sel).forEach(e => e.classList.add('hot'));

/* Srozumitelnost stojí a padá s tímhle: při najetí se do žlábku vypíšou
   OFFSETY slotů na těch řádcích, kam vektor opravdu dopadl. Na prázdných
   řádcích je vidět, jak daleko za větu okno sahá. */
function offsety(v, i) {
  const S = v.model.slots.get(i);
  if (!S) return;
  S.forEach(sl => {
    const radek = v.rows.querySelector(`[data-row="${sl.j}"]`);
    if (!radek) return;
    radek.classList.add('slot');
    const g = radek.querySelector('.gut');
    if (g.dataset.orig === undefined) g.dataset.orig = g.textContent;
    g.textContent = znamenko(sl.d);
  });
}

/** Od šablon doleva: vazby, slovník, řádky pole. */
function doleva(v, ts) {
  const m = v.model;
  ts.forEach(t => {
    znac(v, `.tpl li[data-t="${t}"]`);
    m.links.forEach((L, n) => { if (L.t === t) znac(v, `.lnk li[data-l="${n}"]`); });
    m.byT.get(t).rows.forEach(i => {
      znac(v, `.lex li[data-w="${m.wordOf.get(i).w}"]`);
      const ln = v.rows.querySelector(`.line[data-row="${i}"]`);
      if (ln) ln.classList.add('hot');
    });
  });
}

export function rozsvit(v, druh, id, lex) {
  if (druh === 'row') {
    const i = +id;
    const ln = v.rows.querySelector(`.line[data-row="${i}"]`);
    if (ln) ln.classList.add('hot');
    const x = v.model.out[i];
    if (x.e) {                                   // prázdný řádek → jen <empty>
      const k = lex.idx.get(PRAZDNY_TVAR);
      if (k !== undefined) znac(v, `.lex li[data-w="${k}"]`);
      return;
    }
    offsety(v, i);
    const lk = v.model.wordOf.get(i);
    if (!lk) return;
    const ts = new Set([lk.t]); doleva(v, ts);
    return maluj(v, d => (d.t && ts.has(d.t)) || +d.row === i);
  }
  if (druh === 'w') {
    const k = +id, wd = lex.lex[k];
    znac(v, `.lex li[data-w="${k}"]`);
    if (wd.emp || !wd.rows[v.k].length) {
      wd.rows[v.k].forEach(i => {
        const ln = v.rows.querySelector(`.line[data-row="${i}"]`);
        if (ln) ln.classList.add('hot');
      });
      return;
    }
    const ts = new Set(wd.tids[v.k]); doleva(v, ts); offsety(v, wd.rows[v.k][0]);
    return maluj(v, d => (d.t && ts.has(d.t)) || +d.w === k);
  }
  if (druh === 'l') {
    const n = +id, L = v.model.links[n];
    const ts = new Set([L.t]); doleva(v, ts);
    znac(v, `.lnk li[data-l="${n}"]`); offsety(v, L.occ[0]);
    return maluj(v, d => (d.t && ts.has(d.t)) || +d.l === n);
  }
  if (druh === 't') {
    const ts = new Set([id]); doleva(v, ts);
    offsety(v, v.model.byT.get(id).rows[0]);
    return maluj(v, d => d.t && ts.has(d.t));
  }
}

/** Zhasne obě strany a obnoví to, co je připnuté. */
export function obnov(pohledy, lex) {
  Object.values(pohledy).forEach(zhasni);
  if (stav.pin === null) return;
  const [vk, druh, id] = stav.pin.split(':');
  const v = pohledy[vk];
  if (!v) return;
  rozsvit(v, druh, id, lex);
  const sel = {
    row: `.line[data-row="${id}"]`, w: `.lex li[data-w="${id}"]`,
    l: `.lnk li[data-l="${id}"]`, t: `.tpl li[data-t="${id}"]`,
  }[druh];
  const e = sel && v.root.querySelector(sel);
  if (e) e.classList.add('pinned');
}

export function prepniPin(v, druh, id) {
  const klic = `${v.k}:${druh}:${id}`;
  stav.pin = stav.pin === klic ? null : klic;
}
