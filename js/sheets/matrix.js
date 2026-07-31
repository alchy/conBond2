/* Matice tokeny × vertikály — tady se atributy přiřazují.

   Obě strany vedle sebe schválně: vertikála je sdílená, takže přepínač
   korpusu by jen skrýval půlku toho, na co se dívám. */

import { el, esc, sklon, vetaText } from '../util.js';
import { data, KORPUS, TRIDA_GRUPY, vetyKorpusu } from '../data.js';

export function postavList() {
  const sloupec = (k, jm) => el('div', {}, [
    el('h2', { style: 'font-size:13px', html: jm + ' <span class="pocet" id="mxCnt'
      + k.toUpperCase() + '"></span>' }),
    el('div', { class: 'mxwrap', id: 'mx' + k.toUpperCase() }),
  ]);
  const karta = el('div', { class: 'card', style: 'width:max-content' }, [
    el('h2', {}, 'Matice tokeny × vertikály'),
    el('p', { class: 'hint', style: 'max-width:78ch',
      html: 'Klik do buňky atribut přidá, druhý klik odebere; šablony se přepočítají '
        + 'hned. Sloupce se vybírají zaškrtávátky na listu <b>Vertikály</b> — tady '
        + 'jsou obě strany vedle sebe, protože vertikála platí pro fakta i dotazy.' }),
    el('div', { class: 'two' }, [sloupec('f', 'Fakta'), sloupec('q', 'Dotazy')]),
  ]);
  return el('section', { class: 'sheet', id: 's-mx', hidden: '' }, [karta]);
}

export function prekresli(root, editovane, akce) {
  const cols = data.cols.filter(c => editovane.has(c.a));
  ['f', 'q'].forEach(k => {
    const V = k.toUpperCase();
    const vety = vetyKorpusu(k);
    const obal = root.querySelector('#mx' + V);
    root.querySelector('#mxCnt' + V).textContent =
      sklon(vety.flat().length, 'token', 'tokeny', 'tokenů');
    if (!cols.length) {
      obal.innerHTML = '<p style="color:var(--muted);margin:0">'
        + 'Zaškrtni na listu Vertikály aspoň jednu.</p>';
      return;
    }
    let h = '<table class="mx"><thead><tr><th class="k">#</th><th>tvar</th>'
      + cols.map(c => `<th>${esc(c.a)}</th>`).join('') + '</tr></thead><tbody>';
    vety.forEach((v, z) => {
      h += `<tr class="vs"><td colspan="${cols.length + 2}">${z + 1}. `
        + `${esc(vetaText(vety, z))}</td></tr>`;
      v.forEach((t, i) => {
        h += `<tr class="tok"><td class="k">${z + 1}·${i + 1}</td>`
          + `<td class="f${t.upos === 'PUNCT' ? ' pun' : ''}">${esc(t.form)}</td>`
          + cols.map(c => {
            const ma = t.acts.includes(c.a);
            const trida = TRIDA_GRUPY[c.g] !== undefined ? TRIDA_GRUPY[c.g] : 3;
            return `<td><i class="cell ${ma ? 'g' + trida : 'off'}" data-z="${z}"`
              + ` data-t="${i}" data-a="${esc(c.a)}"`
              + ` title="${esc(t.form + ' · ' + c.a)}"></i></td>`;
          }).join('') + '</tr>';
      });
    });
    obal.innerHTML = h + '</tbody></table>';
    obal.onclick = e => {
      const a = e.target.dataset.a;
      if (a === undefined) return;
      akce.prepniAktivaci(k, +e.target.dataset.z, +e.target.dataset.t, a);
    };
  });
}

export const pocetVybranych = editovane => editovane.size;
export const jmenoKorpusu = k => KORPUS[k].jm;
