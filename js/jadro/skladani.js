/* Skládání otázky ze slovníku — bez věty.

   Otázku nemusíš napsat a nechat rozebrat; můžeš ji poskládat z tvarů, které
   ve slovníku už jsou. Vznikne tím týž druh objektu: uspořádaná posloupnost
   slov, ze které se dá složit vektor stejného tvaru jako z rozebrané věty.

   POŘADÍ JE VÝZNAMNÉ. Šablona není množina, je to vektor s offsety. Kdyby
   bylo skládání neuspořádané, nevznikne z něj vektor, ale pytel — a ten se
   se šablonami z vět nedá porovnat.

   KOTVOU JE TÁZACÍ TVAR. Offsety se počítají od něj, protože právě on určuje,
   na co se ptáme. UD ho nerozliší: kde, kdy, kam, proč a jak mají jeden a týž
   podpis, takže bez vlastní vertikály Ptá= by pět různých otázek spadlo do
   jedné šablony. */

import { znamenko } from './sloty.js';
import { PRAZDNO } from './vektor.js';
import { sadaTvaru } from './model.js';

/** Offsety naklikaných slov vůči kotvě. */
export function offsety(poradi, kotva) {
  return poradi.map((form, i) => ({ form, d: i - kotva }));
}

/**
 * Vektor složené otázky. Aktivace si každé slovo přinese ze slovníku.
 * @param r  ořeže na okno; sloty za oknem se do vektoru nedostanou
 * @returns {vec, mimoOkno[], nezname[], nejiste[]}
 */
export function vektorSlozene(poradi, kotva, lex, { r, cIn, typyOn, poradiAkt }) {
  const rank = a => (poradiAkt.has(a) ? poradiAkt.get(a) : 1e9);
  const vec = [], mimoOkno = [], nezname = [], nejiste = [];

  offsety(poradi, kotva).forEach(({ form, d }) => {
    if (d === 0 && !cIn) return;              // střed mimo vektor, jako v poli
    if (r !== 0 && Math.abs(d) > r) { mimoOkno.push(form); return; }
    if (r === 0 && d !== 0) { mimoOkno.push(form); return; }
    const i = lex.idx.get(form);
    const wd = i === undefined ? null : lex.lex[i];
    const sada = sadaTvaru(wd);
    if (!sada) { nezname.push(form); vec.push(znamenko(d) + ':' + PRAZDNO); return; }
    if (wd.sady.size > 1) nejiste.push(form);
    sada.acts
      .filter(a => typyOn || !a.startsWith('Typ='))
      .slice().sort((p, q) => rank(p) - rank(q))
      .forEach(a => vec.push(znamenko(d) + ':' + a));
  });

  return { vec, mimoOkno, nezname, nejiste };
}

/** Najde mezi hotovými šablonami tu, které se složený vektor rovná. */
export function shodnaSablona(vec, byT) {
  const klic = vec.join('|');
  for (const [t, info] of byT) if (info.vec.join('|') === klic) return t;
  return null;
}

/** Kolik slov ještě padne do okna při daném r — kvůli zašednutí v paletě. */
export const vejdeSe = (d, r, cIn) =>
  (r === 0 ? d === 0 : Math.abs(d) <= r) && (d !== 0 || !!cIn || r === 0);
