/* Skládá bloky dohromady. Sám nepočítá nic — jakmile by tu začal vznikat
   výpočet, patří do jádra; jakmile kreslení, patří do pohledu. */

import { $, $$, el } from './util.js';
import { stav, LISTY, nacti as nactiUI, uloz as ulozUI, srovnejPrepinace } from './stav.js';
import * as D from './data.js';
import * as store from './store.js';
import { poradiAktivaci } from './jadro/vektor.js';
import { postavVse } from './jadro/model.js';
import * as bub from './pohled/bublina.js';
import { zhasni, rozsvit, obnov, prepniPin } from './pohled/svit.js';
import * as korpus from './listy/korpus.js';
import * as defin from './listy/vazby-definice.js';
import * as prehled from './listy/vazby-prehled.js';
import * as vert from './listy/vertikaly.js';
import * as matice from './listy/matice.js';
import * as vety from './listy/vety.js';
import * as dialog from './dialog/nova-veta.js';

const pohledy = {};
const listy = {};
let model = null, mapa = [], editovane = new Set();

/* ---- překreslení ---------------------------------------------------- */
function prekresli() {
  const poradi = poradiAktivaci(D.data.cols);
  model = postavVse(D.data, { ...stav, poradi });

  ['f', 'q'].forEach(k => korpus.prekresli(pohledy[k], model[k], model.slovnik, handlery));
  defin.prekresli(listy.mapd, model, model.slovnik, mapa, akceMapy);
  prehled.prekresli(listy.mapp, model.slovnik, model, mapa, akceMapy);
  vert.prekresli(listy.vert, editovane, akceVertikal);
  matice.prekresli(listy.mx, editovane, akceVertikal);
  vety.prekresli(listy.vety, akceVet);
  vety.tabulkaVazeb(listy.vety, model.slovnik);

  $('#tnF').textContent = D.data.facts.length;
  $('#tnQ').textContent = D.data.query.length;
  $('#tnM').textContent = mapa.length;
  $('#tnV').textContent = D.data.cols.length;
  $('#tnMx').textContent = editovane.size;
  $('#tnS').textContent = vety.pocetVet();
  poHrany();
}

function poHrany() {
  requestAnimationFrame(() => {
    if (pohledy[stav.sheet]) korpus.hrany(pohledy[stav.sheet]);
    if (stav.sheet === 'mapd') defin.hrany(listy.mapd, model);
  });
}

/* ---- obsluha zvýrazňování ------------------------------------------- */
const handlery = {
  najeti: (v, druh, id) => {
    if (stav.pin) return;
    Object.values(pohledy).forEach(zhasni);
    rozsvit(v, druh, id, model.slovnik);
  },
  odjeti: () => { obnov(pohledy, model.slovnik); bub.skryj(); },
  klik: (v, druh, id) => { prepniPin(v, druh, id); obnov(pohledy, model.slovnik); },
  pocetSloupcu: n => {
    const b = $('#c').querySelector('button[data-v="0"]');
    if (b) b.textContent = 'všech ' + n;
  },
};

/* ---- akce jednotlivých listů ---------------------------------------- */
const akceMapy = {
  prepniOznaceni: (k, i) => {
    if (defin.vyber[k].has(i)) defin.vyber[k].delete(i); else defin.vyber[k].add(i);
    defin.prekresli(listy.mapd, model, model.slovnik, mapa, akceMapy);
    poHrany();
  },
  smazDvojici: n => {
    mapa.splice(n, 1);
    store.ulozMapu(store.klicMapy(stav.R), mapa);
    prekresli();
  },
};

const akceVertikal = {
  prepniEditovanou: (a, zapnuto) => {
    if (zapnuto) editovane.add(a); else editovane.delete(a);
    matice.prekresli(listy.mx, editovane, akceVertikal);
    $('#tnMx').textContent = editovane.size;
  },
  smazVertikalu: a => {
    const n = D.pocetTokenu(a);
    if (!confirm(`Smazat vertikálu „${a}“? Zmizí z pole i z ${n} tokenů `
      + 'v obou korpusech a šablony se přepočítají.')) return;
    D.smazVertikalu(a);
    editovane.delete(a);
    store.ulozStav(D.data);
    prekresli();
  },
  prepniAktivaci: (k, z, t, a) => {
    D.prepniAktivaci(k, z, t, a);
    store.ulozStav(D.data);
    prekresli();
  },
};

const akceVet = {
  smazVetu: (k, i) => {
    if (!confirm(`Smazat ${k === 'f' ? 'větu' : 'dotaz'} ${i + 1}?`)) return;
    D.smazVetu(k, i);
    stav.pin = null;
    store.ulozStav(D.data);
    prekresli();
  },
};

/* ---- ovládání -------------------------------------------------------- */
function prepniList(s) {
  stav.sheet = s;
  $$('#tabs button').forEach(b => b.setAttribute('aria-selected', b.dataset.s === s));
  LISTY.forEach(x => { listy[x].hidden = x !== s; });
  $('#globals').hidden = !(s === 'f' || s === 'q');
  bub.skryj();
  ulozUI();
  poHrany();
}

function seg(id, nastav, prepocitatMapu) {
  $$(id + ' button').forEach(b => {
    b.onclick = async () => {
      $$(id + ' button').forEach(x => x.setAttribute('aria-pressed', x === b));
      nastav(+b.dataset.v);
      ulozUI();
      if (prepocitatMapu) { defin.zrusVyber(); await nactiMapu(); }
      prekresli();
    };
  });
}

/* Mapování se zakládá LÍNĚ: první otevření dvojice poloměrů dostane
   předvyplněná data, další už si žije vlastním životem. */
async function nactiMapu() {
  const klic = store.klicMapy(stav.R);
  const nal = await store.nactiMapu(klic);
  mapa = nal ? nal.list : JSON.parse(JSON.stringify(D.vychozi.mapa));
  /* Zapiš, když store nikde není (založ ho), i když je jen v prohlížeči
     a backend mezitím naběhl (přenes ho nahoru). */
  if (!nal || (nal.zdroj === 'local' && store.stavSpojeni.online)) {
    store.ulozMapu(klic, mapa);
  }
}

/* ---- start ----------------------------------------------------------- */
export async function start() {
  bub.priprav();

  const vychozi = await (await fetch('data/vychozi.json', { cache: 'no-store' })).json();
  D.zapamatujVychozi(vychozi);
  const mistni = store.stavZProhlizece(vychozi.query);
  D.nastav(mistni || vychozi);
  editovane = new Set(D.data.cols.filter(c => c.g === 'TYP' || c.g === 'VLASTNÍ')
    .map(c => c.a));

  const hlavni = $('#listy');
  ['f', 'q'].forEach(k => {
    pohledy[k] = korpus.postavList(k);
    listy[k] = pohledy[k].root;
    hlavni.appendChild(pohledy[k].root);
  });
  listy.mapd = defin.postavList();
  listy.mapp = prehled.postavList();
  listy.vert = vert.postavList();
  listy.mx = matice.postavList();
  listy.vety = vety.postavList();
  ['mapd', 'mapp', 'vert', 'mx', 'vety'].forEach(x => hlavni.appendChild(listy[x]));
  document.body.appendChild(dialog.postavDialog());

  nactiUI();
  srovnejPrepinace();
  $$('#tabs button').forEach(b => { b.onclick = () => prepniList(b.dataset.s); });
  seg('#rf', v => { stav.R.f = v; }, true);
  seg('#rq', v => { stav.R.q = v; }, true);
  seg('#p', v => { stav.punct = v; });
  seg('#c', v => { stav.only = v; });
  seg('#cn', v => { stav.cIn = v; });
  seg('#ty', v => { stav.typyOn = v; });

  $('#bSvaz').onclick = () => {
    if (!defin.vyber.q.size || !defin.vyber.f.size) return;
    const tvar = i => model.slovnik.lex[i].form;
    mapa.push({
      id: 'm' + Date.now().toString(36),
      q: [...defin.vyber.q].map(tvar),
      f: [...defin.vyber.f].map(tvar),
    });
    store.ulozMapu(store.klicMapy(stav.R), mapa);
    defin.zrusVyber();
    prekresli();
  };
  $('#bZrus').onclick = () => { defin.zrusVyber(); prekresli(); };

  $('#vAdd').onclick = pridejVertikalu;
  $('#vName').onkeydown = e => {
    if (e.key === 'Enter') { e.preventDefault(); pridejVertikalu(); }
  };
  $('#bNewF').onclick = () => dialog.otevri('f');
  $('#bNewQ').onclick = () => dialog.otevri('q');
  $('#nCut').onclick = () => dialog.rozsekej();
  $('#nParse').onclick = () => dialog.rozeberUdpipem();
  $('#nAdd').onclick = () => {
    const v = dialog.sesbirej();
    if (v.chyba) { $('#nWarn').textContent = v.chyba; return; }
    D.pridejVetu(dialog.cilovyKorpus(), v.tokeny);
    stav.pin = null;
    store.ulozStav(D.data);
    $('#dnew').close();
    prekresli();
  };
  $('#bReset').onclick = () => {
    if (!confirm('Zahodit všechny změny v obou korpusech i vlastní vertikály '
      + 'a vrátit výchozí data? Mapování zůstane.')) return;
    D.naVychozi();
    editovane = new Set(D.data.cols.filter(c => c.g === 'TYP' || c.g === 'VLASTNÍ')
      .map(c => c.a));
    stav.pin = null;
    store.ulozStav(D.data);
    prekresli();
  };
  addEventListener('resize', poHrany);

  /* Nakresli hned z místních dat, ať je něco vidět, a teprve pak se ptej
     backendu. Druhé nactiMapu() je podstatné: to první běželo dřív, než se
     vědělo, jestli server existuje, takže sáhlo jen do prohlížeče. */
  prepniList(stav.sheet);
  await nactiMapu();
  prekresli();

  const zeServeru = await store.ozviSe();
  if (zeServeru) D.nastav(zeServeru);
  else if (store.stavSpojeni.online) store.ulozStav(D.data);
  await nactiMapu();
  prekresli();
}

function pridejVertikalu() {
  const a = $('#vName').value.trim(), g = $('#vGrp').value;
  const chyba = D.pridejVertikalu(a, g);
  $('#vWarn').textContent = chyba || '';
  if (chyba) return;
  editovane.add(a);
  $('#vName').value = '';
  store.ulozStav(D.data);
  prekresli();
}

start();
