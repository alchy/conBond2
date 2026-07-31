/* Vazby · definice — zrcadlo: zleva slovník → vazby → šablony FAKTŮ,
   uprostřed mapování, zprava zpět šablony → vazby → slovník DOTAZŮ.

   Otázky se tu SKLÁDAJÍ, ne píšou. Vybereš tázací tvar, klikáš slova
   v pořadí a vlevo označíš cíl. Skládání samo je v skladani.js; tady je
   jen paleta, ze které se kliká.

   Mapování se kotví na TVARECH, ne na id šablon. Id jsou odvozená — t03 je
   jen pořadí, v jakém vzor vznikl, a přečísluje se při každé změně r. */

import { el, esc, vetaText } from '../util.js';
import { stav } from '../state.js';
import { KORPUS, vetyKorpusu } from '../data.js';
import { klicMapy, stavSpojeni } from '../store.js';
import { vycisti, kresli, stred, rozestup } from '../view/edges.js';
import * as bub from '../view/tooltip.js';
import * as sklad from './compose.js';

/* Slovník je společný a roste s každou zadanou otázkou, takže palet o sto
   položkách je brzo nepřehledná. Filtr má tři vrstvy: text, a hlavně výběr
   otázky, který paletu zúží na její slova. */
export const filtr = { f: '', q: '', veta: -1 };

export function postavList() {
  const paleta = (trida, popis, ul, hledej) =>
    el('div', { class: 'panel ' + trida }, [
      el('div', { class: 'cap' }, popis),
      hledej ? el('div', { class: 'filtr' }, [
        el('input', { type: 'text', class: 'hledej', 'data-k': hledej,
          placeholder: 'filtr…' }),
        hledej === 'q' ? el('select', { class: 'vybraVeta' }) : null,
      ]) : null,
      el('ul', { class: ul }),
    ]);
  const panel = (trida, popis, ul) =>
    el('div', { class: 'panel ' + trida },
      [el('div', { class: 'cap' }, popis), el('ul', { class: ul })]);
  const most = () => el('div', { class: 'span' }, [el('i', {}, 'most mezi světy')]);

  const cols = el('div', { class: 'cols' }, [
    paleta('p-lex', 'slovník · fakta', 'lexF', 'f'),
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
    paleta('p-lex', 'slovník · dotazy', 'lexQ', 'q'),
  ]);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'edges');
  const plocha = el('div', { class: 'stage' }, [cols, svg]);

  const napoveda = el('p', { class: 'hint', style: 'max-width:none;margin:0 0 10px',
    html: 'Otázku nemusíš psát — <b>poskládej ji</b>. Vyber tázací tvar, pak klikej '
      + 'slova ve slovníku dotazů vpravo <b>v pořadí, v jakém by ve větě stála</b>, a '
      + 'vlevo označ, na co to ve faktech míří. Tázací tvar je <b>kotva</b>: offsety '
      + 'se počítají od něj, takže co naklikáš před ní, leží vlevo. Kolik slov má '
      + 'smysl klikat, určuje <b>r_q</b> — co je za oknem, zšedne.' });

  return el('section', { class: 'sheet', id: 's-mapd', hidden: '' },
    [sklad.postavListu(), napoveda, plocha]);
}

/** Prochází paletou: co projde filtrem a jestli je to zrovna ve vzoru. */
function projde(wd, k, vetyFiltr) {
  if (wd.emp || !wd.rows[k].length) return false;
  const text = filtr[k].trim().toLowerCase();
  if (text && !wd.form.includes(text)) return false;
  if (k === 'q' && vetyFiltr && !vetyFiltr.has(wd.form)) return false;
  return true;
}

export function prekresli(root, modely, lex, mapa, akce, poradiAkt) {
  root.querySelector('#mapKey').textContent =
    `${klicMapy(stav.R)}  (dotaz r=${stav.R.q} · fakt r=${stav.R.f})`;
  const odznak = root.querySelector('#stav');
  odznak.textContent = stavSpojeni.online ? 'backend' : 'jen prohlížeč';
  odznak.className = 'stav' + (stavSpojeni.online ? ' on' : '');

  // výběr otázky, který zúží paletu na její slova
  const vyberVety = root.querySelector('.vybraVeta');
  const dotazy = vetyKorpusu('q');
  if (vyberVety.options.length !== dotazy.length + 1) {
    vyberVety.innerHTML = '<option value="-1">— všechna slova —</option>'
      + dotazy.map((v, i) =>
        `<option value="${i}">${esc((i + 1) + '. ' + vetaText(dotazy, i))}</option>`).join('');
  }
  vyberVety.value = String(filtr.veta);
  let vetyFiltr = null;
  if (filtr.veta >= 0 && dotazy[filtr.veta]) {
    vetyFiltr = new Set(dotazy[filtr.veta]
      .filter(t => stav.punct || t.upos !== 'PUNCT')
      .map(t => (stav.punct ? t.form : t.form.toLowerCase())));
  }

  ['f', 'q'].forEach(k => {
    const V = k.toUpperCase(), m = modely[k];
    const ulLex = root.querySelector('.lex' + V);
    const ulLnk = root.querySelector('.lnk' + V);
    const ulTpl = root.querySelector('.tpl' + V);
    ulLex.innerHTML = ''; ulLnk.innerHTML = ''; ulTpl.innerHTML = '';

    const hledej = root.querySelector(`.hledej[data-k="${k}"]`);
    if (hledej && hledej.value !== filtr[k]) hledej.value = filtr[k];

    let skryto = 0;
    lex.lex.forEach((wd, i) => {
      if (wd.emp || !wd.rows[k].length) return;
      if (!projde(wd, k, vetyFiltr)) { skryto++; return; }
      const ve = k === 'q'
        ? sklad.vzor.q.filter(f => f === wd.form).length
        : (sklad.vzor.f.includes(wd.form) ? 1 : 0);
      const li = el('li', {
        class: 'klik' + (ve ? ' oznac' : ''),
        html: `<span class="id">w${String(i + 1).padStart(2, '0')}</span>`
          + `<span class="form">${esc(wd.form)}</span>`
          + (ve > 1 ? `<span class="share">${ve}×</span>`
            : `<span class="share">${wd.tids[k].size}</span>`),
      });
      li.dataset.w = i;
      li.onclick = () => akce.klikSlovo(k, wd.form);
      li.onmouseenter = e => bub.ukaz(
        `<b>${esc(wd.form)}</b> — ${KORPUS[k].jm}, šablon ${wd.tids[k].size}: `
        + ([...wd.tids[k]].join(', ') || '—')
        + `<br>sad aktivací: ${wd.sady.size}`
        + (wd.sady.size > 1 ? ' <b>(nejednoznačné — bere se nejčastější)</b>' : '')
        + '<br><span style="opacity:.75">'
        + (k === 'q' ? 'klik přidá slovo do vzoru' : 'klik označí cíl')
        + '</span>', e);
      li.onmouseleave = bub.skryj;
      ulLex.appendChild(li);
    });
    if (skryto) {
      ulLex.appendChild(el('li', { class: 'skryto' },
        `… ${skryto} skryto filtrem`));
    }

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
    const p = sklad.popisZaznamu(mp);
    const li = el('li', {
      html: (p.typ ? `<span class="pta">${esc(p.typ)}</span>` : '')
        + `<span class="qf">${esc(p.text)}</span>`
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

  root.querySelector('#mapCnt').textContent = mapa.length;
  sklad.prekresli(root, lex, modely.q, poradiAkt, akce);
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
  const p = sklad.popisZaznamu(mp);
  const sq = sablonyProTvary(lex, 'q', mp.q), sf = sablonyProTvary(lex, 'f', mp.f);
  return (p.typ ? `<b>${esc(p.typ)}</b> · ` : '')
    + `<b>${esc(p.text)}</b> ← <b>${esc(mp.f.join(', '))}</b>`
    + `<br>šablon dotazů ${sq.size} (${[...sq].join(', ') || '—'})`
    + `<br>šablon faktů ${sf.size} (${[...sf].join(', ') || '—'})`
    + '<br><span style="opacity:.75">uloženo jako tvary a pořadí; šablony se z toho'
    + ' odvozují, protože jejich id se s r přečíslují</span>';
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
