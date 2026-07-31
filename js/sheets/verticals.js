/* Vertikály — co za osy vůbec existuje. Přiřazuje se na listu Matice. */

import { el, esc } from '../util.js';
import { data, GRUPY, BARVA_GRUPY, POCITANE, jePocitana, pocetTokenu } from '../data.js';

export function postavList() {
  const nova = el('div', { class: 'vnew card' }, [
    el('div', {}, [el('label', { class: 'fld' }, 'Nová vertikála'),
      el('input', { type: 'text', id: 'vName', placeholder: 'Role=agens', size: '24' })]),
    el('div', {}, [el('label', { class: 'fld' }, 'Skupina'),
      el('select', { id: 'vGrp' })]),
    el('button', { class: 'act', id: 'vAdd' }, 'Založit'),
    el('p', { class: 'warn', id: 'vWarn' }),
  ]);
  const karta = el('div', { class: 'card', style: 'width:max-content' }, [
    el('h2', {}, 'Vertikály pole'),
    el('p', { class: 'hint',
      html: 'Vertikála je sloupec pole a platí pro <b>obě strany</b> — je to jeden '
        + 'sdílený atributový prostor. Bez toho by šablona dotazu neměla jak potkat '
        + 'šablonu faktu. Číslo je počet tokenů v obou korpusech dohromady, <b>×</b> '
        + 'vertikálu smaže i z nich.<br>Zaškrtnutá se objeví jako sloupec na listu '
        + '<b>Matice</b>, kde se přiřazuje.' }),
    el('div', { class: 'vlist', id: 'vBody' }),
  ]);
  return el('section', { class: 'sheet', id: 's-vert', hidden: '' }, [nova, karta]);
}

export function prekresli(root, editovane, akce) {
  /* Počítanou skupinu nejde založit ručně — hodnoty do ní dosazuje jádro. */
  root.querySelector('#vGrp').innerHTML = GRUPY.filter(g => g !== POCITANE).map(g =>
    `<option${g === 'VLASTNÍ' ? ' selected' : ''}>${esc(g)}</option>`).join('');

  const telo = root.querySelector('#vBody');
  telo.innerHTML = '';
  GRUPY.filter(g => data.cols.some(c => c.g === g)).forEach(g => {
    const popis = g === POCITANE
      ? ' <small>(počítá se z jemných, needituje se)</small>' : '';
    telo.appendChild(el('div', { class: 'vgrp',
      html: `<i style="color:var(--${BARVA_GRUPY[g] || 'muted'})">${esc(g)}${popis}</i>`
        + data.cols.filter(c => c.g === g).map(c =>
          '<div class="vrow"><label><input type="checkbox" data-a="' + esc(c.a) + '"'
          + (editovane.has(c.a) ? ' checked' : '') + `><span class="nm">${esc(c.a)}</span>`
          + `</label><span class="n">${pocetTokenu(c.a)}</span>`
          + (jePocitana(c) ? '<span class="x" title="počítaná vertikála">·</span>'
             : `<button class="x" data-del="${esc(c.a)}" title="smazat vertikálu">×</button>`)
          + '</div>').join('') }));
  });

  telo.onchange = e => {
    const a = e.target.dataset.a;
    if (a !== undefined) akce.prepniEditovanou(a, e.target.checked);
  };
  telo.onclick = e => {
    const a = e.target.dataset.del;
    if (a !== undefined) akce.smazVertikalu(a);
  };
}
