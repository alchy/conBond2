/* Dialog nové věty. Dvě cesty, jak k tokenům přijít:

   ROZBOREM — lokální UDPipe přes backend. Model je týž, ze kterého vznikla
   výchozí data, takže vrácené aktivace mají v poli už svou vertikálu a
   nová věta nezaloží sloupec navíc.

   RUČNĚ — nabídky se plní z existujících vertikál, takže překlep nemůže
   tiše založit novou. Hodí se, když parser rozebere něco jinak, než
   potřebuješ. */

import { $, el, esc, sklon } from '../util.js';
import { data, KORPUS, GRUPY } from '../data.js';
import { rozeber } from '../store.js';

let korpus = 'f';

export function postavDialog() {
  const form = el('form', { method: 'dialog', class: 'dlg' }, [
    el('h2', { html: '<span id="nNadpis"></span> <span class="kor" id="nKorp"></span>' }),
    el('p', { class: 'hint', style: 'max-width:74ch', id: 'nHint' }),
    el('div', {}, [el('label', { class: 'fld' }, 'Věta'),
      el('textarea', { id: 'nText', rows: '2' })]),
    el('menu', {}, [
      el('button', { type: 'button', class: 'act', id: 'nParse' }, 'Rozebrat UDPipem'),
      el('button', { type: 'button', class: 'act', id: 'nCut' }, 'Rozsekat ručně'),
    ]),
    el('div', { class: 'body', id: 'nToks' }),
    el('p', { class: 'warn', id: 'nWarn' }),
    el('menu', {}, [
      el('button', { type: 'button', class: 'act', id: 'nAdd' }, 'Přidat do pole'),
      el('button', { value: 'x', class: 'act' }, 'Zrušit'),
    ]),
  ]);
  return el('dialog', { id: 'dnew' }, [form]);
}

export function otevri(k) {
  korpus = k;
  $('#nText').value = '';
  $('#nToks').innerHTML = '';
  $('#nWarn').textContent = '';
  $('#nText').placeholder = k === 'q' ? 'Kdo chodí do lesa?' : 'Karel jde ráno do lesa.';
  $('#nNadpis').textContent = k === 'q' ? 'Nový dotaz' : 'Nová věta faktu';
  const e = $('#nKorp'); e.textContent = KORPUS[k].jm; e.className = 'kor ' + k;
  $('#nAdd').textContent = k === 'q' ? 'Přidat mezi dotazy' : 'Přidat mezi fakta';
  $('#nHint').innerHTML =
    '<b>Rozebrat UDPipem</b> pošle větu lokální instanci a vrátí hotové tokeny '
    + 'i s aktivacemi — model je týž, ze kterého jsou výchozí data. '
    + '<b>Rozsekat ručně</b> nic nehádá a atributy vybereš z hodnot, které '
    + 'v poli existují. Novou vertikálu založíš na listu <b>Vertikály</b>.';
  $('#dnew').showModal();
}
export const cilovyKorpus = () => korpus;

const hodnotySkupiny = g => data.cols.filter(c => c.g === g).map(c => c.a);

/* FEATS se v nabídce seskupí podle názvu rysu (Case, Gender, …), jinak je
   to devadesát zaškrtávátek v jedné hromadě. */
function trsy(g) {
  const m = new Map();
  data.cols.filter(c => c.g === g).forEach(c => {
    const n = c.a.indexOf('=') > 0 ? c.a.slice(0, c.a.indexOf('=')) : g;
    if (!m.has(n)) m.set(n, []);
    m.get(n).push(c.a);
  });
  return m;
}
const nabidka = (vals, vybrane) => '<option value=""></option>'
  + vals.map(v => `<option${v === vybrane ? ' selected' : ''}>${esc(v)}</option>`).join('');

/** Postaví editor pro jeden token. `predvolba` = {upos, deprel, feats[]} */
function tokenEditor(tvar, predvolba, otevreny) {
  const d = el('details', { class: 'tok' });
  d.open = otevreny;
  let h = `<summary><span class="nm">${esc(tvar)}</span><span class="sum"></span></summary>`
    + '<div class="hd">'
    + `<div><label class="fld">tvar</label><input type="text" class="f" value="${esc(tvar)}"></div>`
    + `<div><label class="fld">UPOS</label><select class="u">${nabidka(hodnotySkupiny('UPOS'), predvolba.upos)}</select></div>`
    + `<div><label class="fld">DEPREL</label><select class="d">${nabidka(hodnotySkupiny('DEPREL'), predvolba.deprel)}</select></div>`
    + '</div><div class="fgrid">';
  const zvolene = new Set(predvolba.feats || []);
  ['FEATS', 'TYP', 'LEM', 'PTÁ', 'VLASTNÍ'].forEach(g => {
    trsy(g).forEach((vals, nm) => {
      h += `<div class="fg"><i>${esc(nm)}</i>`
        + vals.map(v => `<label><input type="checkbox" value="${esc(v)}"`
          + (zvolene.has(v) ? ' checked' : '') + '>'
          + esc(v.includes('=') ? v.slice(v.indexOf('=') + 1) : v) + '</label>').join('')
        + '</div>';
    });
  });
  d.innerHTML = h + '</div>';
  d.addEventListener('change', () => souhrn(d));
  souhrn(d);
  return d;
}

function souhrn(d) {
  const u = d.querySelector('.u').value, r = d.querySelector('.d').value;
  const n = d.querySelectorAll('input[type=checkbox]:checked').length;
  d.querySelector('.nm').textContent = d.querySelector('.f').value || '—';
  d.querySelector('.sum').textContent =
    (u || '?') + ' · ' + (r || '?') + (n ? ' · ' + sklon(n, 'rys', 'rysy', 'rysů') : '');
}

/** Ruční cesta: rozseká text a nic nehádá kromě interpunkce. */
export function rozsekej() {
  const raw = $('#nText').value.trim();
  const casti = raw.match(/[\p{L}\p{N}]+(?:[-'’][\p{L}\p{N}]+)*|[^\s\p{L}\p{N}]/gu) || [];
  if (!casti.length) { $('#nWarn').textContent = 'Nic k rozsekání.'; return; }
  $('#nWarn').textContent = '';
  const box = $('#nToks'); box.innerHTML = '';
  casti.forEach((f, n) => {
    const jePunct = /^[^\p{L}\p{N}]$/u.test(f);
    box.appendChild(tokenEditor(f,
      jePunct ? { upos: 'PUNCT', deprel: 'punct', feats: [] } : { feats: [] },
      n === 0 && !jePunct));
  });
}

/** Cesta přes rozbor: tokeny přijdou hotové, jen se dají opravit. */
export async function rozeberUdpipem() {
  const text = $('#nText').value.trim();
  if (!text) { $('#nWarn').textContent = 'Napiš nejdřív větu.'; return; }
  $('#nWarn').textContent = 'rozbírám…';
  const o = await rozeber(text);
  if (o.chyba) { $('#nWarn').textContent = o.chyba; return; }
  if (!o.tokeny || !o.tokeny.length) { $('#nWarn').textContent = 'Rozbor nic nevrátil.'; return; }
  const box = $('#nToks'); box.innerHTML = '';
  o.tokeny.forEach((t, n) => box.appendChild(tokenEditor(t.form, {
    upos: t.upos, deprel: t.deprel, feats: t.feats,
  }, n === 0)));
  const nezname = o.nezname || [];
  $('#nWarn').textContent = nezname.length
    ? 'Rozebráno. Pozor, tyhle aktivace v poli zatím nemají vertikálu: '
      + nezname.join(', ')
    : '';
}

/** Sesbírá tokeny z editoru. Vrací {tokeny} nebo {chyba}. */
export function sesbirej() {
  const ds = [...$('#nToks').querySelectorAll('details.tok')];
  if (!ds.length) return { chyba: 'Nejdřív větu rozeber nebo rozsekej.' };
  const tokeny = [], bezUpos = [];
  ds.forEach(d => {
    const form = d.querySelector('.f').value.trim();
    if (!form) return;
    const u = d.querySelector('.u').value, r = d.querySelector('.d').value;
    if (!u) bezUpos.push(form);
    const rysy = [...d.querySelectorAll('input[type=checkbox]:checked')].map(c => c.value);
    const acts = [];
    if (u) acts.push(u);
    if (r) acts.push(r);
    acts.push(...rysy);
    tokeny.push({ form, upos: u || 'X', acts });
  });
  if (!tokeny.length) return { chyba: 'Žádný token nemá tvar.' };
  if (bezUpos.length) {
    return { chyba: 'Bez UPOS: ' + bezUpos.join(', ')
      + ' — bez něj slovo v poli nic nerozsvítí.' };
  }
  return { tokeny };
}

export const skupiny = GRUPY;
