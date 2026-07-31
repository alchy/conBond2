/* Bublina u kurzoru. Jediná na celou stránku, přesouvá se. */

import { $, esc, sklon, vetaText } from '../util.js';
import { stav } from '../stav.js';
import { KORPUS } from '../data.js';

let bublina = null;
export function priprav() { bublina = $('#tip'); }

export function ukaz(html, udalost) {
  bublina.innerHTML = html;
  const r = udalost.target.getBoundingClientRect();
  bublina.style.opacity = 1;
  bublina.style.left = Math.max(8,
    Math.min(r.left, innerWidth - bublina.offsetWidth - 8)) + 'px';
  bublina.style.top = Math.max(8, r.top - bublina.offsetHeight - 8) + 'px';
}
export function skryj() { if (bublina) bublina.style.opacity = 0; }

export const oBunce = (v, x, i, aktivace, sviti) => x.e
  ? `řádek ${i} · <b>prázdný slot</b> — odsazení věty ${x.s + 1}`
    + ` na r=${stav.R[v.k]}; ve slovníku jako <b>&lt;empty&gt;</b>`
  : `řádek ${i} · <b>${esc(aktivace)}</b>${sviti ? '' : ' (nesvítí)'}`
    + ` · slovo <b>„${esc(x.t.form)}“</b><br>${KORPUS[v.k].jm}, věta ${x.s + 1}`
    + `: ${esc(vetaText(v.model.vety, x.s))}`;

export const oTvaru = (v, wd) => {
  const nf = wd.rows.f.length, nq = wd.rows.q.length;
  if (wd.emp) {
    return `<b>&lt;empty&gt;</b> — odsazení vět: ${nf}× ve faktech, ${nq}× v dotazech.`
      + ' Do okolí vstupuje, středem není, takže nemá vlastní šablonu ani vazbu.';
  }
  return `<b>${esc(wd.form)}</b> — slovník je společný<br>`
    + `fakta ${nf}× · dotazy ${nq}×`
    + (nf && nq
      ? '<br>je v obou korpusech — ale to samo nic nespojuje;'
        + ' páruje se až na listu Vazby.<br>šablony faktů: '
        + ([...wd.tids.f].join(', ') || '—') + ' · šablony dotazů: '
        + ([...wd.tids.q].join(', ') || '—')
      : '<br>šablony: ' + ([...wd.tids[v.k]].join(', ') || 'v tomhle korpusu není'));
};

export const oVazbe = (v, L, tvar) =>
  `<b>vazba</b> (${KORPUS[v.k].jm}) w${String(L.w + 1).padStart(2, '0')} · ${L.t}`
  + ` · ${stav.punct ? 'surově' : 'normalizovaně'}`
  + `<br>slovo <b>„${esc(tvar)}“</b>, výskytů ${L.occ.length}`
  + '<br>v kódu: links[(w_id, t_id, zrno)] → výskyty';

export const oSablone = (v, t, info, kdo) => {
  const vety = new Set(info.rows.map(i => v.model.out[i].s));
  const nazvy = (kdo || []).map(x => 'w' + String(x.L.w + 1).padStart(2, '0') + '·' + t);
  return `<b>${t}</b> — obálka okolí (${KORPUS[v.k].jm}, r=${stav.R[v.k]}),`
    + ` bez slova uvnitř<br>${esc(info.vec.join(' · '))}`
    + `<br>↤ ukazuje sem ${sklon(nazvy.length, 'vazba', 'vazby', 'vazeb')}`
    + (nazvy.length ? ': ' + esc(nazvy.join(', ')) : '')
    + `<br>přes ně navěšeno: <b>${esc([...info.words].join(', '))}</b>`
    + (vety.size > 1 ? ' — napříč větami ' + [...vety].map(z => z + 1).join(', ') : '');
};
