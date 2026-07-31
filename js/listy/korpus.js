/* List jedné strany: pole → slovník → vazby → šablony.

   Jeden soubor pro Facts i Query schválně. Původní pole.html mělo vedle
   toks/slots/vec ještě qtoks/qslots/qvec jako souběžnou kopii téhož — a
   právě takové dvojice se rozcházejí. Tady se týž kód zavolá dvakrát
   s jiným korpusem; oddělené facts.js a query.js by byly dva shodné
   soubory, tedy přesně ta chyba, které se vyhýbáme. */

import { el, esc, sklon } from '../util.js';
import { stav } from '../stav.js';
import { data, KORPUS } from '../data.js';
import { pocetSlotu } from '../jadro/sloty.js';
import { sloupce, hlavicka, mrizka } from '../pohled/pole.js';
import { slovnik, vazby, sablony } from '../pohled/panely.js';
import { vycisti, retez, rozestup } from '../pohled/hrany.js';
import * as bub from '../pohled/bublina.js';

const SIRKA_UZKA = 13, SIRKA_SIROKA = 6;

/** Postaví prázdný list a vrátí pohled — sadu prvků, se kterými se pracuje. */
export function postavList(k) {
  const kdo = KORPUS[k].jm;
  const panel = (trida, popis, obsah) =>
    el('div', { class: 'panel ' + trida },
      [el('div', { class: 'cap', html: popis + ' <b class="' + obsah + '-cap"></b>' }),
      ...(trida === 'p-field'
        ? [el('div', { class: 'scroll' }, [el('div', { class: 'grp' }), el('div', { class: 'rows' })])]
        : [el('ul', { class: obsah })])]);

  const cols = el('div', { class: 'cols' }, [
    panel('p-field', '1 · pole ' + kdo, 'capf'),
    el('div', { class: 'bridge' }),
    panel('p-lex', '2 · slovník — společný', 'lex'),
    el('div', { class: 'bridge' }),
    panel('p-lnk', '3 · vazby ' + kdo, 'lnk'),
    el('div', { class: 'bridge' }),
    panel('p-tpl', '4 · šablony ' + kdo, 'tpl'),
  ]);
  const plocha = el('div', { class: 'stage' }, [cols, document.createElementNS(
    'http://www.w3.org/2000/svg', 'svg')]);
  plocha.lastChild.setAttribute('class', 'edges');

  const cisla = el('div', { class: 'foot' }, [
    ['rozměr pole', 'dim'], ['svítí', 'lit'], ['hustota', 'den'],
    ['šablon', 'nt'], ['na středů', 'nw'], ['poměr', 'ratio'],
    ['dosah', 'reach'], ['prázdných slotů', 'pust'],
  ].map(([popis, t]) => el('span', { html: popis + ' <b class="' + t + '"></b>' })));

  const root = el('section', { class: 'sheet', id: 's-' + k }, [plocha, cisla]);

  return {
    k, root, plocha, model: null,
    pole: root.querySelector('.p-field'),
    grp: root.querySelector('.grp'), rows: root.querySelector('.rows'),
    lex: root.querySelector('.lex'), lnk: root.querySelector('.lnk'),
    tpl: root.querySelector('.tpl'), sv: root.querySelector('.edges'),
  };
}

/** Překreslí list z hotového modelu. */
export function prekresli(v, model, lex, handlery) {
  v.model = model;
  const { use, vsech } = sloupce(data.cols, model.out, stav);
  const sirka = stav.only ? SIRKA_UZKA : SIRKA_SIROKA;
  handlery.pocetSloupcu(vsech);

  hlavicka(v.grp, data.cols, use, sirka);
  const sviti = mrizka(v.rows, model, data.cols, use, sirka, {
    najeti: (i, akt, trefa, e) => {
      handlery.najeti(v, 'row', i);
      bub.ukaz(bub.oBunce(v, model.out[i], i, akt, trefa), e);
    },
    odjeti: handlery.odjeti,
    klik: i => handlery.klik(v, 'row', i),
  });

  const wire = (li, druh, id, co) => {
    li.classList.add('klik');
    li.onmouseenter = e => {
      handlery.najeti(v, druh, id);
      if (druh === 'w') bub.ukaz(bub.oTvaru(v, co), e);
      if (druh === 'l') bub.ukaz(bub.oVazbe(v, co, lex.lex[co.w].form), e);
      if (druh === 't') bub.ukaz(bub.oSablone(v, id, co.info, co.kdo), e);
    };
    li.onmouseleave = handlery.odjeti;
    li.onclick = () => handlery.klik(v, druh, id);
  };
  slovnik(v.lex, lex.lex, v.k, wire);
  vazby(v.lnk, model.links, wire);
  sablony(v.tpl, model.byT, model.links, wire);

  cisla(v, model, lex, use.length, sviti);
}

function cisla(v, m, lex, sloupcu, sviti) {
  const q = s => v.root.querySelector(s);
  const r = stav.R[v.k];
  const radku = m.out.length;
  const prazdnych = m.own.reduce((n, o) =>
    n + m.slots.get(o.i).filter(s => m.out[s.j] && m.out[s.j].e).length, 0);
  const vsechSlotu = m.own.reduce((n, o) => n + m.slots.get(o.i).length, 0);
  q('.capf-cap').textContent = `(${radku} × ${sloupcu}, r=${r})`;
  q('.lex-cap').textContent = `(${lex.lex.length})`;
  q('.lnk-cap').textContent =
    `(${m.links.length} · ${stav.punct ? 'surově' : 'normalizovaně'})`;
  q('.tpl-cap').textContent = `(${m.byT.size})`;
  q('.dim').textContent = `${radku} × ${sloupcu}`;
  q('.lit').textContent = sviti;
  q('.den').textContent = (radku && sloupcu
    ? (100 * sviti / (radku * sloupcu)).toFixed(1) : '0.0') + ' %';
  q('.nt').textContent = m.byT.size;
  q('.nw').textContent = m.own.length;
  q('.ratio').textContent = m.own.length ? (m.byT.size / m.own.length).toFixed(2) : '—';
  q('.reach').textContent = r === 0 ? '1 slot — jen střed'
    : sklon(pocetSlotu({ r, cIn: stav.cIn }), 'slot', 'sloty', 'slotů');
  q('.pust').textContent = vsechSlotu
    ? `${prazdnych} z ${vsechSlotu} (${(100 * prazdnych / vsechSlotu).toFixed(0)} %)` : '—';
}

/** Hrany se počítají z getBoundingClientRect, a ten na skrytém listu vrací
    nuly. Kreslí se proto až když je list opravdu vidět. */
export function hrany(v) {
  if (!v.model || stav.sheet !== v.k) return;
  rozestup(v.plocha);
  const sv = v.sv;
  vycisti(sv, v.plocha);
  const sdilena = t => (v.model.byT.get(t) || { words: new Set() }).words.size > 1;
  retez(sv, v.plocha, v, v.model, sdilena);
}
