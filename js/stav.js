/* Nastavení pohledu — co je zrovna vidět a jak. Nejsou to data, proto to
   nejde do backendu, ale do prohlížeče: r se přepíná pořád a ztrácet ho
   při každém načtení je otrava.

   POLOMĚR JE DVOJÍ. Dotaz smí mít jiné r než fakt, protože se vektory obou
   stran nikdy neporovnávají přímo — mapování je kotvené na tvarech. */

import { $$ } from './util.js';

const KLIC = 'pole2/ui';

export const stav = {
  R: { f: 1, q: 1 },
  punct: 0,          // 0 = normalizovaně (bez interpunkce, malými)
  only: 1,           // 1 = jen svítící sloupce
  cIn: 0,            // střed uvnitř vektoru
  typyOn: 1,         // významový typ v poli i ve vektoru
  sheet: 'f',
  pin: null,         // připnuté zvýraznění "strana:druh:id"
};

export const LISTY = ['f', 'q', 'mapd', 'mapp', 'vert', 'mx', 'vety'];

/* r=1 je výchozí schválně: při vyšším r je s plnými FEATS poměr šablon ke
   středům skoro 1.00, každé slovo má vlastní vzor a nesbíhá se ani jedna
   hrana. Sdílení se vrací zúžením okna nebo ubráním vertikál. */
export function nacti() {
  let u = null;
  try { u = JSON.parse(localStorage.getItem(KLIC) || 'null'); } catch (e) { /* prázdno */ }
  if (!u) return;
  const cele = (x, lo, hi, d) => (Number.isInteger(x) && x >= lo && x <= hi ? x : d);
  if (u.R) { stav.R.f = cele(u.R.f, 0, 8, 1); stav.R.q = cele(u.R.q, 0, 8, 1); }
  stav.punct = cele(u.punct, 0, 1, 0);
  stav.only = cele(u.only, 0, 1, 1);
  stav.cIn = cele(u.cIn, 0, 1, 0);
  stav.typyOn = cele(u.typyOn, 0, 1, 1);
  if (LISTY.includes(u.sheet)) stav.sheet = u.sheet;
}

export function uloz() {
  const { R, punct, only, cIn, typyOn, sheet } = stav;
  try { localStorage.setItem(KLIC, JSON.stringify({ R, punct, only, cIn, typyOn, sheet })); }
  catch (e) { /* prázdno */ }
}

/* Tlačítka se srovnají podle stavu, ne naopak — jinak by se po načtení
   tvářila stisknutá ta, co jsou tak napsaná v HTML. */
export function srovnejPrepinace() {
  const set = (sel, v) => $$(sel + ' button').forEach(b =>
    b.setAttribute('aria-pressed', +b.dataset.v === v));
  set('#rf', stav.R.f); set('#rq', stav.R.q);
  set('#p', stav.punct); set('#c', stav.only);
  set('#cn', stav.cIn); set('#ty', stav.typyOn);
}
