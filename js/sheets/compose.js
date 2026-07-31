/* Skládání otázky klikáním — lišta nad zrcadlem.

   Otázka se nemusí psát. Vybereš tázací tvar, pak klikáš slova ve slovníku
   v pořadí, v jakém by ve větě stála, a vlevo označíš, na co to ve faktech
   míří. Vznikne vzor, který má stejný tvar jako šablona z rozebrané věty.

   POŘADÍ JE VÝZNAMNÉ a tázací tvar je KOTVA — offsety se počítají od něj.
   Kotva nemusí být první: co naklikáš před ní, leží vlevo. */

import { el, esc, sklon } from '../util.js';
import { stav } from '../state.js';
import { data } from '../data.js';
import { znamenko } from '../model.js';

/* Vektor složené otázky počítá JÁDRO na backendu, ne prohlížeč. Sem přijde
   hotový; drží se v `posledni`, aby se nemusel volat server při každém
   překreslení lišty. */
export let posledni = null;
export function zapamatuj(odpoved) { posledni = odpoved; }

/** Offsety se počítají i tady, ale jen pro kreslení chipů — autoritou je
    to, co vrátí jádro v `posledni.offsety`. */
export function offsety(poradi, kotva) {
  return poradi.map((form, i) => ({ form, d: kotva < 0 ? 0 : i - kotva }));
}

/** Rozdělaný vzor. `kotva` je index tázacího tvaru v `q`, -1 = zatím žádný. */
export const vzor = { q: [], kotva: -1, f: [] };

export function vycisti() { vzor.q = []; vzor.kotva = -1; vzor.f = []; }

export function pridejSlovo(form) { vzor.q.push(form); }
export function pridejKotvu(form) { vzor.q.push(form); vzor.kotva = vzor.q.length - 1; }
export function odeberSlovo(i) {
  vzor.q.splice(i, 1);
  if (i === vzor.kotva) vzor.kotva = -1;
  else if (i < vzor.kotva) vzor.kotva--;
}
export function prepniCil(form) {
  const i = vzor.f.indexOf(form);
  if (i < 0) vzor.f.push(form); else vzor.f.splice(i, 1);
}
export const hotovy = () => vzor.q.length > 0 && vzor.kotva >= 0 && vzor.f.length > 0;

/** Tázací tvary — vlastní vertikála, kterou UD nedává. */
export const tazaciTvary = () => data.cols
  .filter(c => c.g === 'PTÁ')
  .map(c => c.a.slice(c.a.indexOf('=') + 1));

export function postavListu() {
  return el('div', { class: 'skladac' }, [
    el('div', { class: 'radek' }, [
      el('span', { class: 'popis' }, 'tázací tvar'),
      el('span', { class: 'pta', id: 'ptaPaleta' }),
    ]),
    el('div', { class: 'radek' }, [
      el('span', { class: 'popis' }, 'vzor otázky'),
      el('span', { class: 'chipy', id: 'vzorQ' }),
    ]),
    el('div', { class: 'radek' }, [
      el('span', { class: 'popis' }, 'cíl ve faktech'),
      el('span', { class: 'chipy', id: 'vzorF' }),
    ]),
    el('div', { class: 'radek' }, [
      el('span', { class: 'popis' }, 'vektor'),
      el('span', { class: 'vysledek', id: 'vzorVec' }),
    ]),
    el('div', { class: 'radek' }, [
      el('button', { class: 'act', id: 'bSvaz' }, 'Svázat jako vzor'),
      el('button', { class: 'act', id: 'bZrus' }, 'Zrušit'),
      el('span', { class: 'cnt', html: 'dvojic <b id="mapCnt"></b>' }),
      el('span', { class: 'cnt', style: 'color:var(--muted)',
        html: 'store <b id="mapKey"></b>' }),
      el('span', { class: 'stav', id: 'stav' }),
    ]),
  ]);
}

export function prekresli(root, lex, modelQ, poradiAkt, akce) {
  // paleta tázacích tvarů
  const paleta = root.querySelector('#ptaPaleta');
  paleta.innerHTML = '';
  tazaciTvary().forEach(f => {
    const b = el('button', {
      class: 'chip pta' + (vzor.kotva >= 0 && vzor.q[vzor.kotva] === f ? ' aktivni' : ''),
    }, f);
    b.onclick = () => akce.kotva(f);
    paleta.appendChild(b);
  });

  // naklikaná slova i s offsety
  const qq = root.querySelector('#vzorQ');
  qq.innerHTML = '';
  if (!vzor.q.length) {
    qq.appendChild(el('span', { class: 'prazdno' },
      'zvol tázací tvar a pak klikej slova ve slovníku dotazů vpravo'));
  } else {
    const r = stav.R.q;
    offsety(vzor.q, vzor.kotva).forEach(({ form, d }, i) => {
      const mimo = vzor.kotva >= 0 && (r === 0 ? d !== 0 : Math.abs(d) > r);
      const b = el('button', {
        class: 'chip' + (i === vzor.kotva ? ' kotva' : '') + (mimo ? ' mimo' : ''),
        title: mimo ? `offset ${znamenko(d)} je za oknem r_q=${r}, do vektoru nevstoupí`
          : 'klik odebere',
      }, (vzor.kotva >= 0 ? znamenko(d) + ' ' : '') + form);
      b.onclick = () => akce.odeber(i);
      qq.appendChild(b);
    });
  }

  // cíle ve faktech
  const ff = root.querySelector('#vzorF');
  ff.innerHTML = '';
  if (!vzor.f.length) {
    ff.appendChild(el('span', { class: 'prazdno' },
      'klikni slova ve slovníku faktů vlevo'));
  } else {
    vzor.f.forEach(form => {
      const b = el('button', { class: 'chip cil', title: 'klik odebere' }, form);
      b.onclick = () => akce.odeberCil(form);
      ff.appendChild(b);
    });
  }

  // vektor a jeho zdraví — hotový z jádra
  const vv = root.querySelector('#vzorVec');
  if (vzor.kotva < 0 || !vzor.q.length) {
    vv.innerHTML = '<span class="prazdno">bez kotvy vektor nevznikne — '
      + 'tázací tvar určuje, od čeho se offsety počítají</span>';
  } else if (!posledni) {
    vv.innerHTML = '<span class="prazdno">počítá jádro…</span>';
  } else {
    const v = posledni;
    vv.innerHTML = (v.vektor.length
      ? `<code>${esc(v.vektor.slice(0, 6).join(' '))}${v.vektor.length > 6 ? ' …' : ''}</code>`
        + ` <span class="cnt">${sklon(v.vektor.length, 'položka', 'položky', 'položek')}</span>`
      : '<span class="prazdno">prázdný — všechno vypadlo z okna</span>')
      + (v.shoda ? ` <span class="shoda">= ${v.shoda}</span>`
        : ' <span class="cnt">nová šablona</span>')
      + (v.mimo_okno.length
        ? ` <span class="varovani">za oknem: ${esc(v.mimo_okno.join(', '))}</span>` : '')
      + (v.nejiste.length
        ? ` <span class="varovani">nejisté aktivace: ${esc(v.nejiste.join(', '))}</span>` : '')
      + (v.nezname.length
        ? ` <span class="varovani">bez aktivací: ${esc(v.nezname.join(', '))}</span>` : '');
  }

  root.querySelector('#bSvaz').disabled = !hotovy();
}

/** Hotový vzor pro uložení. Tvar drží i pořadí a kotvu, aby šel obnovit. */
export function doZaznamu() {
  return {
    id: 'm' + Date.now().toString(36),
    typ: vzor.q[vzor.kotva],
    q: vzor.q.slice(),
    kotva: vzor.kotva,
    f: vzor.f.slice(),
  };
}

/** Popis dvojice do seznamu. Starší záznamy kotvu nemají — jsou to množiny. */
export function popisZaznamu(mp) {
  if (typeof mp.kotva !== 'number' || mp.kotva < 0) {
    return { typ: null, text: mp.q.join(', ') };
  }
  return {
    typ: mp.typ || mp.q[mp.kotva],
    text: offsety(mp.q, mp.kotva).map(o => znamenko(o.d) + ':' + o.form).join(' '),
  };
}
