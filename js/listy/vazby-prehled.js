/* Vazby · přehled — co je svázané a které vzory to rozsvítilo.

   Dvojice drží tvary; šablony ve sloupcích se z nich odvozují při každém
   kreslení, takže se mění s poloměrem. Kolik faktových vzorů visí na jednom
   dotazovém, je rovnou míra dvojznačnosti toho dotazu. */

import { el, esc } from '../util.js';
import { stavSpojeni } from '../store.js';
import { sablonyProTvary } from './vazby-definice.js';

export function postavList() {
  const lista = el('div', { class: 'mapbar' }, [
    el('span', { class: 'cnt', html: 'dvojic <b id="pDvojic"></b>' }),
    el('span', { class: 'cnt', html: 'aktivováno šablon dotazů <b id="pQ"></b>' }),
    el('span', { class: 'cnt', html: 'šablon faktů <b id="pF"></b>' }),
    el('span', { class: 'cnt',
      html: 'nejvíc faktových vzorů na jeden dotazový <b id="pNej"></b>' }),
    el('span', { class: 'stav', id: 'stav2' }),
  ]);
  const napoveda = el('p', { class: 'hint', style: 'max-width:none;margin:0 0 10px',
    html: 'Dvojice drží <b>tvary</b>; šablony vpravo se z nich odvozují při každém '
      + 'kreslení, takže se mění s poloměrem — proto má každá dvojice poloměrů '
      + 'vlastní store. Kolik faktových vzorů visí na jednom dotazovém, je rovnou '
      + 'míra dvojznačnosti toho dotazu.' });
  const karta = el('div', { class: 'card', style: 'width:max-content' },
    [el('div', { id: 'pTab', style: 'max-height:66vh;overflow:auto' })]);
  return el('section', { class: 'sheet', id: 's-mapp', hidden: '' },
    [lista, napoveda, karta]);
}

export function prekresli(root, lex, modely, mapa, akce) {
  const rady = mapa.map((mp, n) => ({
    n, mp,
    sq: sablonyProTvary(lex, 'q', mp.q),
    sf: sablonyProTvary(lex, 'f', mp.f),
  }));
  const aktQ = new Set(), aktF = new Set();
  rady.forEach(r => { r.sq.forEach(t => aktQ.add(t)); r.sf.forEach(t => aktF.add(t)); });

  const naJeden = new Map();
  rady.forEach(r => r.sq.forEach(t => {
    if (!naJeden.has(t)) naJeden.set(t, new Set());
    r.sf.forEach(x => naJeden.get(t).add(x));
  }));
  const nej = naJeden.size ? Math.max(...[...naJeden.values()].map(S => S.size)) : 0;

  root.querySelector('#pDvojic').textContent = mapa.length;
  root.querySelector('#pQ').textContent = `${aktQ.size} z ${modely.q.byT.size}`;
  root.querySelector('#pF').textContent = `${aktF.size} z ${modely.f.byT.size}`;
  root.querySelector('#pNej').textContent = nej;
  const odznak = root.querySelector('#stav2');
  odznak.textContent = stavSpojeni.online ? 'backend' : 'jen prohlížeč';
  odznak.className = 'stav' + (stavSpojeni.online ? ' on' : '');

  const tid = S => [...S].map(t => `<span class="tid">${t}</span>`).join(' ') || '—';
  root.querySelector('#pTab').innerHTML =
    '<table class="vaz"><tr><th>#</th><th>tvary dotazu</th><th>tvary faktu</th>'
    + '<th>šablony dotazu</th><th>šablony faktu</th><th>dvojznačnost</th><th></th></tr>'
    + rady.map(r => {
      const nic = !r.sq.size || !r.sf.size;
      const dvoj = [...r.sq].reduce(
        (m, t) => Math.max(m, (naJeden.get(t) || new Set()).size), 0);
      return `<tr${nic ? ' class="mez"' : ''}><td class="n">${r.n + 1}</td>`
        + `<td class="qf">${esc(r.mp.q.join(', '))}</td>`
        + `<td class="ff">${esc(r.mp.f.join(', '))}</td>`
        + `<td>${tid(r.sq)}</td><td>${tid(r.sf)}</td>`
        + `<td class="n">${nic ? '—' : dvoj + '×'}</td>`
        + `<td><button class="x" data-delp="${r.n}" title="smazat dvojici">×</button></td>`
        + '</tr>';
    }).join('') + '</table>';

  root.querySelector('#pTab').onclick = e => {
    const n = e.target.dataset.delp;
    if (n !== undefined) akce.smazDvojici(+n);
  };
}
