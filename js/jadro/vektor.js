/* Vektor = obálka okolí. Pro každý slot se vezmou všechny aktivace toho
   řádku a předřadí se jim offset: "-1:ADJ -1:amod +1:NOUN".

   Dvě věci, na kterých to stojí:

   1. POŘADÍ AKTIVACÍ JE VÝZNAMNÉ. Vektor je řetězec, takže dvě slova s touž
      sadou aktivací, ale jinak seřazenou, by dostala různé šablony. Matice
      metadat aktivace přidává na konec, takže by je rozbila. Proto se před
      složením vždy srovnají do pořadí sloupců pole.

   2. Prázdný řádek přispívá jediným ∅. Ve slovníku má vlastní tvar. */

export const PRAZDNO = '∅';
export const PRAZDNY_TVAR = '<empty>';

/** Mapa aktivace → index sloupce. Definuje kanonické pořadí. */
export function poradiAktivaci(cols) {
  const m = new Map();
  cols.forEach((c, i) => m.set(c.a, i));
  return m;
}

/** Aktivace jednoho řádku, odfiltrované a v kanonickém pořadí. */
export function aktivace(x, { typyOn, poradi }) {
  if (x.e) return [PRAZDNO];
  const rank = a => (poradi.has(a) ? poradi.get(a) : 1e9);
  return x.t.acts
    .filter(a => typyOn || !a.startsWith('Typ='))
    .slice()
    .sort((p, q) => rank(p) - rank(q));
}

/** Vektor pro dané sloty. Chybějící řádek se čte jako prázdno. */
export function vektor(out, S, opts, znamenko) {
  return S.flatMap(sl => {
    const y = out[sl.j];
    return y
      ? aktivace(y, opts).map(a => znamenko(sl.d) + ':' + a)
      : [znamenko(sl.d) + ':' + PRAZDNO];
  });
}
