/* Vazby · definice — zrcadlo: zleva slovník → vazby → šablony FAKTŮ,
   uprostřed mapování, zprava zpět šablony → vazby → slovník DOTAZŮ.

   Mapování se kotví na TVARECH, ne na id šablon. Id jsou odvozená — t03 je
   jen pořadí, v jakém vzor vznikl, a přečísluje se při každé změně r. Tvar
   je data. Dvojice šablon se z tvarů odvodí až při kreslení. */

import { el, esc } from '../util.js';
import { stav } from '../stav.js';
import { KORPUS } from '../data.js';
import { klicMapy, stavSpojeni } from '../store.js';
import { vycisti, kresli, stred, rozestup } from '../pohled/hrany.js';
import * as bub from '../pohled/bublina.js';

export const vyber = { f: new Set(), q: new Set() };
export function zrusVyber() { vyber.f.clear(); vyber.q.clear(); }

export function postavList() {
  const panel = (trida, popis, ul) =>
    el('div', { class: 'panel ' + trida },
      [el('div', { class: 'cap' }, popis), el('ul', { class: ul })]);
  const most = () => el('div', { class: 'span' }, [el('i', {}, 'most mezi světy')]);

  const cols = el('div', { class: 'cols' }, [
    panel('p-lex', 'slovník · fakta', 'lexF'),
    el('div', { class: 'bridge' }),
    panel('p-lnk', 'vazby faktů', 'lnkF'),
    el('div', { class: 'bridge' }),
    panel('p-tpl', 'šablony faktů', 'tplF'),
    most(),
    panel('p-map', 'mapování', 'mapL'),
    most(),
    panel('p-tpl', 'šablony dotazů', 'tplQ'),
    el('div', { class: 'bridge' }),
    panel('p-lnk', 'vazby dotazů', 'lnkQ'),
    el('div', { class: 'bridge' }),
    panel('p-lex', 'slovník · dotazy', 'lexQ'),
  ]);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'edges');
  const plocha = el('div', { class: 'stage' }, [cols, svg]);

  const lista = el('div', { class: 'mapbar' }, [
    el('span', { class: 'cnt', id: 'selCnt' }),
    el('button', { class: 'act', id: 'bSvaz' }, 'Svázat označené'),
    el('button', { class: 'act', id: 'bZrus' }, 'Zrušit výběr'),
    el('span', { class: 'cnt', html: 'dvojic <b id="mapCnt"></b>' }),
    el('span', { class: 'cnt', style: 'color:var(--muted)',
      html: 'store <b id="mapKey"></b>' }),
    el('span', { class: 'stav', id: 'stav' }),
  ]);
  const napoveda = el('p', { class: 'hint', style: 'max-width:none;margin:0 0 10px',
    html: 'Označ slovo ve <b>slovníku dotazů</b> vpravo — začne blikat. Pak označ '
      + 'slovo ve <b>slovníku faktů</b> vlevo. Takhle vyber celou sadu a stiskni '
      + '<b>Svázat označené</b>. Dvojice se uloží jako <b>množina tvarů</b>, ne jako '
      + 'id šablon — ta jsou odvozená a s každou změnou r se přečíslují.' });

  return el('section', { class: 'sheet', id: 's-mapd', hidden: '' },
    [lista, napoveda, plocha]);
}

export function prekresli(root, modely, lex, mapa, akce) {
  root.querySelector('#mapKey').textContent =
    `${klicMapy(stav.R)}  (dotaz r=${stav.R.q} · fakt r=${stav.R.f})`;
  const odznak = root.querySelector('#stav');
  odznak.textContent = stavSpojeni.online ? 'backend' : 'jen prohlížeč';
  odznak.className = 'stav' + (stavSpojeni.online ? ' on' : '');

  ['f', 'q'].forEach(k => {
    const V = k.toUpperCase(), m = modely[k];
    const ulLex = root.querySelector('.lex' + V);
    const ulLnk = root.querySelector('.lnk' + V);
    const ulTpl = root.querySelector('.tpl' + V);
    ulLex.innerHTML = ''; ulLnk.innerHTML = ''; ulTpl.innerHTML = '';

    lex.lex.forEach((wd, i) => {
      if (!wd.rows[k].length || wd.emp) return;
      const li = el('li', {
        class: 'klik' + (vyber[k].has(i) ? ' oznac' : ''),
        html: `<span class="id">w${String(i + 1).padStart(2, '0')}</span>`
          + `<span class="form">${esc(wd.form)}</span>`
          + `<span class="share">${wd.tids[k].size}</span>`,
      });
      li.dataset.w = i;
      li.onclick = () => akce.prepniOznaceni(k, i);
      li.onmouseenter = e => bub.ukaz(
        `<b>${esc(wd.form)}</b> — ${KORPUS[k].jm}, šablon ${wd.tids[k].size}: `
        + ([...wd.tids[k]].join(', ') || '—')
        + '<br><span style="opacity:.75">klik označí; označené se svážou '
        + 'tlačítkem nahoře</span>', e);
      li.onmouseleave = bub.skryj;
      ulLex.appendChild(li);
    });

    m.links.forEach((L, n) => {
      const li = el('li', {
        html: `<span class="id">w${String(L.w + 1).padStart(2, '0')}·${L.t}</span>`
          + `<span class="share">${L.occ.length}×</span>`,
      });
      li.dataset.l = n; li.dataset.w = L.w; li.dataset.t = L.t;
      ulLnk.appendChild(li);
    });

    [...m.byT.entries()].forEach(([t, info]) => {
      const li = el('li', {
        html: `<span class="id">${t}</span><span class="vec">`
          + esc(info.vec.slice(0, 2).join(' ') + (info.vec.length > 2 ? ' …' : ''))
          + '</span>',
      });
      li.dataset.t = t;
      li.onmouseenter = e => bub.ukaz(
        `<b>${t}</b> (${KORPUS[k].jm}, r=${stav.R[k]})<br>${esc(info.vec.join(' · '))}`
        + `<br>slova: <b>${esc([...info.words].join(', '))}</b>`, e);
      li.onmouseleave = bub.skryj;
      ulTpl.appendChild(li);
    });
  });

  const ul = root.querySelector('.mapL');
  ul.innerHTML = '';
  mapa.forEach((mp, n) => {
    const li = el('li', {
      html: `<span class="qf">${esc(mp.q.join(', '))}</span>`
        + '<span class="ar">←</span>'
        + `<span class="ff">${esc(mp.f.join(', '))}</span>`
        + `<button class="x" data-delm="${n}" title="smazat dvojici">×</button>`,
    });
    li.dataset.m = n;
    li.onmouseenter = e => { zvyrazni(root, mp, lex); bub.ukaz(oDvojici(mp, lex), e); };
    li.onmouseleave = () => { odznac(root); bub.skryj(); };
    ul.appendChild(li);
  });
  ul.onclick = e => {
    const n = e.target.dataset.delm;
    if (n !== undefined) akce.smazDvojici(+n);
  };

  root.querySelector('#selCnt').innerHTML =
    `označeno <b>${vyber.q.size}</b> v dotazech · <b>${vyber.f.size}</b> ve faktech`;
  root.querySelector('#bSvaz').disabled = !(vyber.q.size && vyber.f.size);
  root.querySelector('#mapCnt').textContent = mapa.length;
}

/** Z tvarů odvodí šablony — tvar je kotva, id se přečíslují. */
export function sablonyProTvary(lex, k, formy) {
  const out = new Set();
  formy.forEach(f => {
    const i = lex.idx.get(stav.punct ? f : f.toLowerCase());
    if (i !== undefined) lex.lex[i].tids[k].forEach(t => out.add(t));
  });
  return out;
}

function zvyrazni(root, mp, lex) {
  odznac(root);
  ['q', 'f'].forEach(k => {
    const V = k.toUpperCase();
    sablonyProTvary(lex, k, mp[k]).forEach(t => {
      const li = root.querySelector(`.tpl${V} [data-t="${t}"]`);
      if (li) li.classList.add('hot');
      root.querySelectorAll(`.lnk${V} [data-t="${t}"]`)
        .forEach(e => e.classList.add('hot'));
    });
    mp[k].forEach(f => {
      const i = lex.idx.get(stav.punct ? f : f.toLowerCase());
      if (i === undefined) return;
      const li = root.querySelector(`.lex${V} [data-w="${i}"]`);
      if (li) li.classList.add('hot');
    });
  });
}
const odznac = root => root.querySelectorAll('li.hot').forEach(e => e.classList.remove('hot'));

function oDvojici(mp, lex) {
  const sq = sablonyProTvary(lex, 'q', mp.q), sf = sablonyProTvary(lex, 'f', mp.f);
  return `<b>${esc(mp.q.join(', '))}</b> ← <b>${esc(mp.f.join(', '))}</b>`
    + `<br>šablon dotazů ${sq.size} (${[...sq].join(', ') || '—'})`
    + `<br>šablon faktů ${sf.size} (${[...sf].join(', ') || '—'})`
    + '<br><span style="opacity:.75">dvojice je uložená jako množina tvarů;'
    + ' šablony se z ní odvozují, protože jejich id se s r přečíslují</span>';
}

export function hrany(root, modely) {
  if (stav.sheet !== 'mapd') return;
  const plocha = root.querySelector('.stage');
  rozestup(plocha);
  const sv = root.querySelector('.edges');
  vycisti(sv, plocha);
  ['f', 'q'].forEach(k => {
    const V = k.toUpperCase(), m = modely[k];
    /* Fakta jdou zleva doprava, dotazy zrcadlově zprava doleva — proto se
       u dotazů prohodí strany, ze kterých hrana vychází. */
    const a = k === 'f' ? 'r' : 'l', b = k === 'f' ? 'l' : 'r';
    m.links.forEach((L, n) => {
      const lx = root.querySelector(`.lex${V} [data-w="${L.w}"]`);
      const ln = root.querySelector(`.lnk${V} [data-l="${n}"]`);
      const tl = root.querySelector(`.tpl${V} [data-t="${L.t}"]`);
      if (!ln) return;
      if (lx) kresli(sv, stred(plocha, lx, a), stred(plocha, ln, b), '', { w: L.w, t: L.t });
      if (tl) kresli(sv, stred(plocha, ln, a), stred(plocha, tl, b), '', { w: L.w, t: L.t });
    });
  });
}
