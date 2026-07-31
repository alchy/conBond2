/* Tři panely vpravo od pole: slovník, vazby, šablony.

   Slovník se kreslí CELÝ na obou stranách — je společný. Tvar, který
   v tomhle korpusu není, se jen vybledne, aby bylo jasné, proč z něj
   nevede hrana. */

import { el, esc } from '../util.js';

export function slovnik(cil, lex, strana, wire) {
  cil.innerHTML = '';
  lex.forEach((wd, k) => {
    const doma = wd.rows[strana].length;
    const cizi = wd.rows[strana === 'f' ? 'q' : 'f'].length;
    const li = el('li', {
      class: (wd.emp ? 'emp ' : '') + (doma ? '' : 'cizi'),
      html: `<span class="id">w${String(k + 1).padStart(2, '0')}</span>`
        + `<span class="form">${esc(wd.form)}</span>`
        + (doma && cizi ? '<span class="obe">F·Q</span>'
          : doma > 1 ? `<span class="share">${doma}×</span>` : ''),
    });
    li.dataset.w = k;
    wire(li, 'w', k, wd);
    cil.appendChild(li);
  });
}

export function vazby(cil, links, wire) {
  cil.innerHTML = '';
  links.forEach((L, n) => {
    const li = el('li', {
      html: `<span class="id">w${String(L.w + 1).padStart(2, '0')}·${L.t}</span>`
        + `<span class="share">${L.occ.length}×</span>`,
    });
    li.dataset.l = n; li.dataset.w = L.w; li.dataset.t = L.t;
    wire(li, 'l', n, L);
    cil.appendChild(li);
  });
}

/* Vazba se jmenuje w01·t03, takže pojmenuje oba své konce. Šablona o svých
   vazbách dřív neříkala nic — odkaz vedl jen jedním směrem. Odznak „N ↤"
   ho dělá obousměrným. */
export function sablony(cil, byT, links, wire) {
  cil.innerHTML = '';
  [...byT.entries()].forEach(([t, info]) => {
    const kdo = links.map((L, n) => ({ L, n })).filter(x => x.L.t === t);
    const li = el('li', {
      html: `<span class="id">${t}</span>`
        + `<span class="vec">${esc(info.vec.slice(0, 3).join(' ')
          + (info.vec.length > 3 ? ' …' : ''))}</span>`
        + `<span class="share zpet">${kdo.length}&#8199;↤</span>`
        + (info.words.size > 1 ? `<span class="share">${info.words.size} slova</span>` : ''),
    });
    li.dataset.t = t;
    wire(li, 't', t, { info, kdo });
    cil.appendChild(li);
  });
}
