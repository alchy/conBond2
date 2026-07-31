/* Vzory — pohled, který velký korpus unese.

   Mřížka se u 59 106 řádků vykreslit nedá a nemá to smysl ani zkoušet.
   Šablona ale řádky nepotřebuje: čte se z vektoru a ze seznamu tvarů, které
   ji sdílejí. Přesně to je na velkém korpusu ta zajímavá věc — že vzor
   „…a X na konci věty" sdílí 189 různých slov.

   Čísla jsou z CELÉHO pole, ne z výřezu. Kdyby se počítala z toho, co je
   zrovna na obrazovce, vypadalo by to, že se všechno sdílí. */

import { el, esc } from '../util.js';

export const RAZENI = [
  ['velikost', 'kolik slov sdílí'],
  ['vyskyty', 'kolik výskytů'],
  ['delka', 'délka vektoru'],
  ['id', 'podle id'],
];

export const stav = { strana: 'f', od: 0, pocet: 40, razeni: 'velikost', hledat: '' };

export function postavList() {
  const lista = el('div', { class: 'mapbar' }, [
    el('div', {}, [el('label', { class: 'fld' }, 'Strana'),
      el('div', { class: 'seg', id: 'vzStrana' }, [
        el('button', { 'data-v': 'f', 'aria-pressed': 'true' }, 'fakta'),
        el('button', { 'data-v': 'q' }, 'dotazy')])]),
    el('div', {}, [el('label', { class: 'fld' }, 'Řadit'),
      el('select', { id: 'vzRazeni' },
        RAZENI.map(([k, p]) => el('option', { value: k }, p)))]),
    el('div', {}, [el('label', { class: 'fld' }, 'Hledat tvar'),
      el('input', { type: 'text', id: 'vzHledat', size: '16',
        placeholder: 'např. narodil' })]),
    el('span', { class: 'cnt', id: 'vzPocet' }),
    el('button', { class: 'lehke', id: 'vzZpet' }, '‹ zpět'),
    el('button', { class: 'lehke', id: 'vzDal' }, 'dál ›'),
  ]);
  const karta = el('div', { class: 'card' }, [
    el('h2', {}, 'Vzory'),
    el('p', { class: 'hint', html:
      'Šablona je obálka okolí pro zvolené <b>r</b>, sloučená tam, kde vyšla '
      + 'stejně. <b>Sdílí</b> je počet různých tvarů, které na týž vzor padly '
      + '— čím vyšší, tím obecnější místo ve větě.<br>Čísla jsou z celého '
      + 'pole, ne z výřezu na listech Facts a Query.' }),
    el('div', { class: 'vzory', id: 'vzTelo' }),
  ]);
  return el('section', { class: 'sheet', id: 's-vz', hidden: '' }, [lista, karta]);
}

export function prekresli(root, data) {
  if (!root || !data) return;
  const konec = Math.min(data.od + stav.pocet, data.celkem);
  root.querySelector('#vzPocet').innerHTML = data.celkem
    ? `<b>${data.od + 1}–${konec}</b> z ${data.celkem} šablon`
    : 'žádná šablona nesedí';
  root.querySelector('#vzZpet').disabled = data.od <= 0;
  root.querySelector('#vzDal').disabled = konec >= data.celkem;

  root.querySelector('#vzTelo').innerHTML = data.sablony.map(s => {
    const sloty = s.vec.map(a => {
      const [off, akt] = [a.slice(0, a.indexOf(':')), a.slice(a.indexOf(':') + 1)];
      return `<i class="sl" data-o="${esc(off)}">${esc(akt)}</i>`;
    }).join('');
    return `<div class="vz"><div class="hlava"><b>${esc(s.id)}</b>`
      + `<span class="mira" title="kolik různých tvarů vzor sdílí">${s.tvaru}</span>`
      + `<span class="vyskyt">${s.vyskytu}× · ${s.delka} slotů</span></div>`
      + `<div class="vec">${sloty}</div>`
      + `<div class="tvary">${s.ukazka.map(t => esc(t)).join(' · ')}`
      + (s.tvaru > s.ukazka.length ? ` <span class="vic">…a dalších `
         + `${s.tvaru - s.ukazka.length}</span>` : '') + '</div></div>';
  }).join('');
}
