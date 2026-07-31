/* Test jádra bez prohlížeče. Dřív musel tenhle soubor vytahovat funkce
   z HTML regulárem; teď si je prostě naimportuje — to je hlavní výhoda
   toho rozdělení. Spuštění:  node test/jadro.mjs                        */
import { readFileSync } from 'node:fs';
import { tok, stredy } from '../js/jadro/tok.js';
import { sloty, pocetSlotu, znamenko } from '../js/jadro/sloty.js';
import { poradiAktivaci, aktivace, vektor, PRAZDNY_TVAR } from '../js/jadro/vektor.js';
import { postavVse, klicTvaru } from '../js/jadro/model.js';
import { offsety, vektorSlozene, shodnaSablona } from '../js/jadro/skladani.js';

const D = JSON.parse(readFileSync(new URL('../data/vychozi.json', import.meta.url)));
const poradi = poradiAktivaci(D.cols);

let chyb = 0;
const ok = (podminka, zprava) => { if (!podminka) { chyb++; console.log('  ✗ ' + zprava); } };
const nast = (o = {}) => ({ R: { f: 1, q: 1 }, punct: 0, cIn: 0, typyOn: 1, poradi, ...o });

console.log('— odsazení drží hranice vět, oba korpusy, r 0–8 —');
console.log('r | fakta: řádků/středů/šablon | dotazy: řádků/středů/šablon | mimo | přes');
for (let r = 0; r <= 8; r++) {
  const M = postavVse(D, nast({ R: { f: r, q: r } }));
  let mimo = 0, pres = 0;
  ['f', 'q'].forEach(k => {
    M[k].own.forEach(o => M[k].slots.get(o.i).forEach(s => {
      const y = M[k].out[s.j];
      if (!y) mimo++; else if (y.s !== o.x.s) pres++;
    }));
  });
  console.log([r,
    `${M.f.out.length}/${M.f.own.length}/${M.f.byT.size}`,
    `${M.q.out.length}/${M.q.own.length}/${M.q.byT.size}`,
    mimo, pres].join(' | '));
  ok(mimo === 0, `r=${r}: ${mimo} slotů míří mimo pole`);
  ok(pres === 0, `r=${r}: ${pres} slotů přelezlo do sousední věty`);
  ok(M.f.own.length === 75, `r=${r}: středů faktů ${M.f.own.length}, čekáno 75`);
  ok(M.q.own.length === 260, `r=${r}: středů dotazů ${M.q.own.length}, čekáno 260`);
  const maPrazdno = M.slovnik.idx.has(PRAZDNY_TVAR);
  ok(maPrazdno === (r > 0), `r=${r}: <empty> ve slovníku = ${maPrazdno}`);
}

console.log('\n— r se smí lišit mezi stranami —');
{
  const M = postavVse(D, nast({ R: { f: 1, q: 4 } }));
  console.log(`  fakta r=1 → ${M.f.byT.size} šablon · dotazy r=4 → ${M.q.byT.size} šablon`);
  ok(pocetSlotu({ r: 1, cIn: 0 }) === 2 && pocetSlotu({ r: 4, cIn: 0 }) === 8,
    'počet slotů se neliší podle strany');
  ok(M.f.byT.size !== M.q.byT.size, 'různá r dala stejný počet šablon — podezřelé');
}

console.log('\n— slovník je společný, šablony a vazby ne —');
{
  const M = postavVse(D, nast());
  const lex = M.slovnik.lex;
  const vObou = lex.filter(w => !w.emp && w.rows.f.length && w.rows.q.length);
  const jenF = lex.filter(w => !w.emp && w.rows.f.length && !w.rows.q.length);
  const jenQ = lex.filter(w => !w.emp && !w.rows.f.length && w.rows.q.length);
  console.log(`  slovník ${lex.length} · jen fakta ${jenF.length}`
    + ` · jen dotazy ${jenQ.length} · v obou ${vObou.length}`);
  console.log(`  vazby: fakta ${M.f.links.length} · dotazy ${M.q.links.length}`);
  ok(lex.length === 104, `slovník ${lex.length}, čekáno 104`);
  ok(vObou.length === 38, `v obou ${vObou.length}, čekáno 38`);
  ok(M.f.byT.size === 71 && M.q.byT.size === 161, 'počty šablon nesedí');
  ok(M.f.links.length === 74 && M.q.links.length === 210, 'počty vazeb nesedí');
  // zpětný odkaz: součet vazeb na šablonu musí dát počet vazeb
  ['f', 'q'].forEach(k => {
    const zpet = [...M[k].byT.keys()]
      .map(t => M[k].links.filter(L => L.t === t).length)
      .reduce((a, b) => a + b, 0);
    ok(zpet === M[k].links.length,
      `${k}: zpětných odkazů ${zpet}, vazeb ${M[k].links.length}`);
  });
  ok([...M.f.byT.keys()].every(t => t[0] === 't'), 'šablony faktů nemají předponu t');
  ok([...M.q.byT.keys()].every(t => t[0] === 'q'), 'šablony dotazů nemají předponu q');
}

console.log('\n— vypnutý významový typ nesmí Typ= pustit do vektoru —');
{
  const M = postavVse(D, nast({ typyOn: 0 }));
  const s = [...M.f.byT.values()].flatMap(i => i.vec).filter(a => a.includes(':Typ='));
  console.log('  slotů s Typ=:', s.length);
  ok(s.length === 0, 'Typ= prosáklo do vektoru i při vypnutém přepínači');
}

console.log('\n— pořadí aktivací je kanonické —');
{
  const t = { acts: ['Case=Nom', 'PROPN', 'nsubj'] };
  const a = aktivace({ t }, { typyOn: 1, poradi }).join(' ');
  const b = aktivace({ t: { acts: ['nsubj', 'Case=Nom', 'PROPN'] } },
    { typyOn: 1, poradi }).join(' ');
  console.log('  ', a);
  ok(a === b, 'přeházené pořadí acts dalo jiný vektor → šablony by se rozpadly');
}

console.log('\n— okraje věty dostanou ∅ —');
{
  const M = postavVse(D, nast());
  const prvni = M.f.own.find(o => o.x.s === 0);
  const posledni = M.f.own.filter(o => o.x.s === 0).pop();
  const v = i => vektor(M.f.out, M.f.slots.get(i), { typyOn: 1, poradi }, znamenko);
  console.log('  „' + prvni.x.t.form + '“ →', v(prvni.i).slice(0, 3).join(' '), '…');
  ok(v(prvni.i).includes('-1:∅'), 'první slovo věty nemá vlevo ∅');
  ok(v(posledni.i).includes('+1:∅'), 'poslední slovo věty nemá vpravo ∅');
}

console.log('\n— tok a klíč tvaru —');
{
  const out = tok(D.facts, { r: 2, punct: 1 });
  console.log('  se surovým zrnem:', stredy(out).length, 'středů (s interpunkcí)');
  ok(stredy(out).length === 86, 'surové zrno nedalo 86 středů');
  ok(klicTvaru('Karel', 0) === 'karel' && klicTvaru('Karel', 1) === 'Karel',
    'klicTvaru nerespektuje zrno');
}

console.log('\n— tázací tvar rozděluje to, co UD slévá —');
{
  const kolidujici = ['jak', 'kdy', 'kam', 'kde', 'proč'];
  const bezPta = new Set(), sPta = new Set();
  D.query.flat().forEach(t => {
    if (!t.acts.some(a => a.startsWith('PronType=Int'))) return;
    if (!kolidujici.includes(t.form.toLowerCase())) return;
    bezPta.add(t.acts.filter(a => !a.startsWith('Ptá=')).slice().sort().join('|'));
    sPta.add(t.acts.slice().sort().join('|'));
  });
  console.log(`  ${kolidujici.join(', ')}: bez Ptá= ${bezPta.size} podpis`
    + `, s Ptá= ${sPta.size}`);
  ok(bezPta.size === 1, 'čekal jsem, že tyhle tvary bez Ptá= splývají do jednoho');
  ok(sPta.size === kolidujici.length, 'Ptá= je nerozdělil na samostatné');
}

console.log('\n— skládání otázky ze slovníku —');
{
  const M = postavVse(D, nast());
  const opts = { r: 2, cIn: 0, typyOn: 1, poradiAkt: poradi };
  // „se jmenuje KDO alfons" — kotva uprostřed, tedy offsety -2 -1 0 +1
  const poradiSlov = ['se', 'jmenuje', 'kdo', 'alfons'];
  console.log('  offsety:', offsety(poradiSlov, 2).map(o => `${o.form}(${o.d})`).join(' '));
  const v = vektorSlozene(poradiSlov, 2, M.slovnik, opts);
  console.log('  vektor:', v.vec.slice(0, 4).join(' '), '…', `(${v.vec.length} položek)`);
  console.log('  mimo okno:', v.mimoOkno.join(', ') || 'nic',
    '· neznámé:', v.nezname.join(', ') || 'nic',
    '· nejisté:', v.nejiste.join(', ') || 'nic');
  ok(offsety(poradiSlov, 2).map(o => o.d).join(',') === '-2,-1,0,1', 'offsety nesedí');
  ok(!v.vec.some(a => a.startsWith('0:')), 'střed se dostal do vektoru, ač cIn=0');
  ok(v.nezname.length === 0, 'některý tvar nemá ve slovníku aktivace');
  // s r=1 musí dvě krajní slova vypadnout z okna
  const uzsi = vektorSlozene(poradiSlov, 2, M.slovnik, { ...opts, r: 1 });
  console.log('  při r=1 vypadne:', uzsi.mimoOkno.join(', '));
  ok(uzsi.mimoOkno.includes('se'), 'r=1 nevyřadilo slovo na offsetu -2');
  ok(uzsi.vec.length < v.vec.length, 'užší okno nedalo kratší vektor');
  // shoda s hotovou šablonou
  const t = shodnaSablona(v.vec, M.q.byT);
  console.log('  shoduje se s hotovou šablonou dotazů:', t || 'ne');
}

console.log('\n— stavový automat skládání (bez DOM) —');
{
  const S = await import('../js/listy/skladani.js');
  S.vycisti();
  ok(!S.hotovy(), 'prázdný vzor se tváří jako hotový');
  S.pridejSlovo('se');
  S.pridejSlovo('jmenuje');
  ok(!S.hotovy(), 'vzor bez kotvy se tváří jako hotový');
  S.pridejKotvu('kdo');
  S.pridejSlovo('alfons');
  console.log('  po naklikání:', S.vzor.q.join(' '), '· kotva na indexu', S.vzor.kotva);
  ok(S.vzor.kotva === 2, `kotva má být 2, je ${S.vzor.kotva}`);
  ok(!S.hotovy(), 'vzor bez cíle se tváří jako hotový');
  S.prepniCil('pes');
  ok(S.hotovy(), 'úplný vzor se netváří jako hotový');
  S.prepniCil('pes');
  ok(!S.hotovy(), 'odebrání cíle se neprojevilo');
  S.prepniCil('pes');

  // odebrání slova PŘED kotvou musí kotvu posunout
  S.odeberSlovo(0);
  console.log('  po odebrání „se":', S.vzor.q.join(' '), '· kotva', S.vzor.kotva);
  ok(S.vzor.kotva === 1, `kotva se neposunula: ${S.vzor.kotva}`);
  ok(S.vzor.q[S.vzor.kotva] === 'kdo', 'kotva ukazuje na jiné slovo než kdo');

  const z = S.doZaznamu();
  console.log('  záznam:', JSON.stringify({ typ: z.typ, q: z.q, kotva: z.kotva, f: z.f }));
  ok(z.typ === 'kdo', 'typ záznamu nesedí s kotvou');
  const p = S.popisZaznamu(z);
  console.log('  popis:', p.typ, '·', p.text);
  ok(p.text === '-1:jmenuje 0:kdo +1:alfons', 'popis s offsety nesedí: ' + p.text);

  // odebrání kotvy ji musí zrušit, ne posunout na cizí slovo
  S.odeberSlovo(S.vzor.kotva);
  ok(S.vzor.kotva === -1, 'odebrání kotvy ji nezrušilo');

  // starší záznam bez kotvy se musí číst jako množina
  const stary = S.popisZaznamu({ q: ['kdo'], f: ['psa'] });
  console.log('  starší záznam bez kotvy:', stary.typ, '·', stary.text);
  ok(stary.typ === null && stary.text === 'kdo', 'starý záznam se čte špatně');
  S.vycisti();
}

console.log(chyb ? `\n${chyb} KONTROL SELHALO` : '\nvšechny kontroly prošly');
process.exit(chyb ? 1 : 0);
