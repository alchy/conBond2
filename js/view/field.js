/* Mřížka pole: řádek na slovo, sloupec na aktivaci.

   Vypnutý významový typ musí zmizet i z POLE, ne jen z vektoru — jinak
   pole přestane být obrázkem té šablony, kterou ukazuje panel šablon. */

import { el, esc, vetaText } from '../util.js';
import { BARVA_GRUPY, TRIDA_GRUPY } from '../data.js';
import { PRAZDNO } from '../model.js';

/** Které sloupce se kreslí. Vrací indexy do cols, -1 je sloupec prázdna. */
export function sloupce(cols, out, { only, typyOn }) {
  const idx = cols.map((c, i) => i).filter(i => typyOn || !cols[i].a.startsWith('Typ='));
  const svitici = i => out.some(x => !x.e && x.t.acts.includes(cols[i].a));
  return { use: [-1].concat(only ? idx.filter(svitici) : idx), vsech: idx.length };
}

/** Pásma vertikál nad mřížkou. Odsazení 27px = šířka žlábku. */
export function hlavicka(cil, cols, use, sirka) {
  const pasma = [];
  use.forEach(ci => {
    const g = ci === -1 ? '∅' : cols[ci].g;
    if (pasma.length && pasma[pasma.length - 1].g === g) pasma[pasma.length - 1].n++;
    else pasma.push({ g, n: 1 });
  });
  cil.innerHTML = '';
  cil.appendChild(el('div', { class: 'pad' }));
  cil.appendChild(el('div', { class: 'bands' }, pasma.map(b =>
    el('div', {
      style: `width:${b.n * sirka + b.n - 1}px;color:var(--${BARVA_GRUPY[b.g] || 'muted'})`,
    }, b.g))));
}

/**
 * Vykreslí mřížku. Vrací počet rozsvícených buněk.
 * @param handlery {najeti(i, aktivace, sviti, udalost), odjeti(), klik(i)}
 */
export function mrizka(cil, { out, vety }, cols, use, sirka, handlery) {
  cil.innerHTML = '';
  let sviti = 0;
  out.forEach((x, i) => {
    const radek = el('div', { class: 'line klik' });
    const zlabek = el('span', { class: 'gut' }, (!x.e && x.k === 0) ? (x.s + 1) + '.' : '');
    radek.appendChild(zlabek);

    const rw = el('div', { class: 'rw' });
    rw.style.gridTemplateColumns = `repeat(${use.length},${sirka}px)`;
    const ma = x.e ? null : new Set(x.t.acts);
    use.forEach(ci => {
      const trefa = ci === -1 ? !!x.e : (ma && ma.has(cols[ci].a));
      const trida = ci === -1 ? 'b'
        : (TRIDA_GRUPY[cols[ci].g] !== undefined ? TRIDA_GRUPY[cols[ci].g] : 3);
      const bunka = el('div', { class: 'c' + (trefa ? ' g' + trida : '') });
      if (trefa) sviti++;
      bunka.onmouseenter = e =>
        handlery.najeti(i, ci === -1 ? PRAZDNO : cols[ci].a, trefa, e);
      bunka.onmouseleave = handlery.odjeti;
      rw.appendChild(bunka);
    });
    radek.dataset.row = i;
    radek.dataset.sent = x.s;
    if (!x.e) radek.onclick = () => handlery.klik(i);
    radek.appendChild(rw);
    cil.appendChild(radek);

    /* Věta pod svým blokem. Hranici drží odsazení, tenhle popisek ji
       pojmenuje — dřív tu práci dělal řádek rámu. */
    if (i === out.length - 1 || out[i + 1].s !== x.s) {
      cil.appendChild(el('div', { class: 'sent',
        html: `<b>${x.s + 1}.</b>${esc(vetaText(vety, x.s))}` }));
    }
  });
  return sviti;
}
