/* Tok tokenů přes celý korpus.
   Jediné, co tenhle blok umí: srovnat věty za sebe a odsadit je.

   Každá věta dostane r prázdných řádků na obou koncích. Mezi posledním
   slovem jedné věty a prvním slovem druhé tak leží vždy 2r prázdných
   řádků, takže okno NEMÁ JAK přelézt hranici — hranici drží sama
   geometrie. Rám věty, poloměr ve větách ani příznak přechodu proto
   nejsou potřeba; dřívější verze je měla a byla to zbytečná složitost. */

/** @returns pole řádků: {t, s, k} pro slovo, {e:true, s} pro prázdný slot */
export function tok(vety, { r, punct }) {
  const out = [];
  vety.forEach((src, z) => {
    const ts = punct ? src : src.filter(t => t.upos !== 'PUNCT');
    for (let p = 0; p < r; p++) out.push({ e: true, s: z });
    ts.forEach((t, k) => out.push({ t, s: z, k }));
    for (let p = 0; p < r; p++) out.push({ e: true, s: z });
  });
  return out;
}

/** Řádky, které jsou skutečné slovo — tedy možné středy vektoru. */
export function stredy(out) {
  return out.map((x, i) => ({ x, i })).filter(o => !o.x.e);
}
