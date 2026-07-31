/* Sloty vektoru: kam kolem středu vektor dopadá a s jakým offsetem.

   Díky odsazení v tok.js je to čisté počítání indexů — sloty středu i jsou
   i-r … i+r a všechny vždycky existují. Dřívější verze musela hlídat okraje
   pole i hranice vět a měla na to čtyřicet řádků; odsazení tu práci udělalo
   za ni. */

/** @returns [{j, d}] — j je index řádku, d offset od středu */
export function sloty(i, { r, cIn }) {
  if (r === 0) return [{ j: i, d: 0 }];
  const S = [];
  for (let d = -r; d <= r; d++) {
    if (d === 0) { if (cIn) S.push({ j: i, d: 0 }); continue; }
    S.push({ j: i + d, d });
  }
  return S;
}

/** Kolik slotů má vektor při daném nastavení. */
export function pocetSlotu({ r, cIn }) {
  return r === 0 ? 1 : 2 * r + (cIn ? 1 : 0);
}

export const znamenko = d => (d > 0 ? '+' + d : '' + d);
