/* Data: vertikály a oba korpusy. Jediné místo, kde se mění — kdo chce
   něco změnit, volá tyhle funkce, nesahá do polí přímo.

   Vertikály jsou SPOLEČNÉ oběma stranám. Bez toho by měly vektory obou
   stran jiný atributový prostor a jejich šablony by se nemohly potkat. */

export const data = { cols: [], facts: [], query: [] };
export let vychozi = null;      // pro tlačítko „Výchozí data"

export const KORPUS = {
  f: { klic: 'facts', jm: 'fakta', predpona: 't' },
  q: { klic: 'query', jm: 'dotazy', predpona: 'q' },
};

export const GRUPY = ['UPOS', 'DEPREL', 'FEATS', 'TYP', 'LEM', 'PTÁ', 'VLASTNÍ'];
/* Typ, Lem, tázací tvar a vlastní atributy jsou NAŠE vrstva, ne rozborová —
   proto inkoust, ne další barva. Co nedává UDPipe, patří vizuálně k sobě.
   PTÁ je tázací TVAR, ne lemma: „co" a „koho" jsou různé otázky s různými
   odpověďmi, ale totéž lemma. */
export const BARVA_GRUPY = {
  '∅': 'muted', UPOS: 'upos', DEPREL: 'deprel', FEATS: 'feats',
  TYP: 'ink', LEM: 'ink2', 'PTÁ': 'ink', 'VLASTNÍ': 'ink',
};
export const TRIDA_GRUPY = { UPOS: 0, DEPREL: 1, FEATS: 2, TYP: 3, LEM: 4,
                             'PTÁ': 3, 'VLASTNÍ': 3 };

const kopie = o => JSON.parse(JSON.stringify(o));

export function nastav(zdroj) {
  data.cols = kopie(zdroj.cols);
  data.facts = kopie(zdroj.facts);
  data.query = kopie(zdroj.query);
}
export function zapamatujVychozi(zdroj) { vychozi = kopie(zdroj); }
export function naVychozi() { nastav(vychozi); }

export const vetyKorpusu = k => data[KORPUS[k].klic];

/** Kolik tokenů v OBOU korpusech nese danou aktivaci. */
export const pocetTokenu = a =>
  data.facts.flat().concat(data.query.flat()).filter(t => t.acts.includes(a)).length;

/* Nová vertikála jde na konec SVÉ skupiny, ne na konec pole — pásma
   v hlavičce se skládají ze sousedních sloupců téže vertikály a rozpadla
   by se na dvě. */
export function pridejVertikalu(a, g) {
  if (!a) return 'Zadej název.';
  if (a.includes('|')) return 'Svislítko nesmí být — odděluje sloty ve vektoru.';
  if (data.cols.some(c => c.a === a)) return 'Taková vertikála už existuje.';
  let kam = data.cols.length;
  for (let i = data.cols.length - 1; i >= 0; i--) {
    if (data.cols[i].g === g) { kam = i + 1; break; }
  }
  data.cols.splice(kam, 0, { a, g });
  return null;
}

export function smazVertikalu(a) {
  data.cols = data.cols.filter(c => c.a !== a);
  ['facts', 'query'].forEach(kk => data[kk].forEach(v => v.forEach(t => {
    const i = t.acts.indexOf(a);
    if (i >= 0) t.acts.splice(i, 1);
  })));
}

/** Přepne aktivaci na jednom tokenu. Vrací nový stav (true = má ji). */
export function prepniAktivaci(k, veta, token, a) {
  const t = vetyKorpusu(k)[veta][token];
  const i = t.acts.indexOf(a);
  if (i < 0) { t.acts.push(a); return true; }
  t.acts.splice(i, 1);
  return false;
}

export function pridejVetu(k, tokeny) { vetyKorpusu(k).push(tokeny); }
export function smazVetu(k, i) { vetyKorpusu(k).splice(i, 1); }
