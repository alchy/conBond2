/* Věty — oba korpusy vedle sebe, každý se svým tlačítkem.

   Dřív tu byl jeden seznam a přepínač korpusu; dalo se přehlédnout, do
   které strany věta spadne. Dva sloupce ten omyl neumožňují. */

import { el, esc, sklon, vetaText } from '../util.js';
import { data, vetyKorpusu } from '../data.js';

export function postavList() {
  const sloupec = (k, jm, tlacitko) => el('div', { class: 'card vetyCol' }, [
    el('h2', { html: jm + ' <span class="pocet" id="cnt' + k.toUpperCase() + '"></span>' }),
    el('div', { class: 'vety', id: 'vety' + k.toUpperCase() }),
    tlacitko,
  ]);
  const tl = (id, html) =>
    el('button', { class: 'act', id, style: 'margin-top:12px', html });

  return el('section', { class: 'sheet', id: 's-vety', hidden: '' }, [
    el('div', { class: 'two' }, [
      sloupec('f', 'Fakta', tl('bNewF', '+ Nová věta <b>faktu</b>')),
      sloupec('q', 'Dotazy', tl('bNewQ', '+ Nový <b>dotaz</b>')),
    ]),
    el('menu', { style: 'display:flex;gap:8px;margin:14px 0 0;padding:0' },
      [el('button', { class: 'act warn', id: 'bReset' }, 'Výchozí data')]),
    el('details', { class: 'tab' }, [
      el('summary', {}, 'Tabulka vazeb — slovo ↔ šablony obou stran'),
      el('div', { id: 'tab' }),
    ]),
  ]);
}

export function prekresli(root, akce) {
  ['f', 'q'].forEach(k => {
    const V = k.toUpperCase(), vety = vetyKorpusu(k);
    root.querySelector('#cnt' + V).textContent = sklon(vety.length, 'věta', 'věty', 'vět');
    const telo = root.querySelector('#vety' + V);
    telo.innerHTML = vety.length
      ? vety.map((v, i) => '<div class="vt">'
        + `<span class="num">${i + 1}.</span>`
        + `<span class="tx">${esc(vetaText(vety, i))}</span>`
        + `<span class="n">${sklon(v.length, 'token', 'tokeny', 'tokenů')}</span>`
        + `<button class="x" data-del-v="${i}" title="smazat">×</button></div>`).join('')
      : '<p style="color:var(--muted);margin:0">Zatím nic — přidej tlačítkem níž.</p>';
    telo.onclick = e => {
      const i = e.target.dataset.delV;
      if (i !== undefined) akce.smazVetu(k, +i);
    };
  });
}

/** Tabulka: který tvar má jaké šablony na které straně. */
export function tabulkaVazeb(root, lex) {
  root.querySelector('#tab').innerHTML =
    '<table class="vaz"><tr><th>w_id</th><th>tvar</th><th>fakta</th><th>dotazy</th>'
    + '<th>šablony faktů</th><th>šablony dotazů</th></tr>'
    + lex.lex.map((wd, k) => wd.emp ? '' :
      `<tr><td class="n">w${String(k + 1).padStart(2, '0')}</td>`
      + `<td>${esc(wd.form)}</td><td class="n">${wd.rows.f.length}</td>`
      + `<td class="n">${wd.rows.q.length}</td>`
      + `<td class="n">${[...wd.tids.f].join(', ') || '—'}</td>`
      + `<td class="n">${[...wd.tids.q].join(', ') || '—'}</td></tr>`).join('')
    + '</table>';
}

export const pocetVet = () => data.facts.length + data.query.length;
