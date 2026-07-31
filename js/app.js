/* Skládá bloky dohromady. Sám nepočítá nic — jakmile by tu začal vznikat
   výpočet, patří do jádra; jakmile kreslení, patří do pohledu. */

import { $, $$, el } from './util.js';
import { stav, LISTY, nacti as nactiUI, uloz as ulozUI, srovnejPrepinace } from './state.js';
import * as D from './data.js';
import * as store from './store.js';
import { prevzit } from './model.js';
import * as bub from './view/tooltip.js';
import { zhasni, rozsvit, obnov, prepniPin } from './view/highlight.js';
import * as korpus from './sheets/corpus.js';
import * as defin from './sheets/links-define.js';
import * as sklad from './sheets/compose.js';
import * as prehled from './sheets/links-overview.js';
import * as vert from './sheets/verticals.js';
import * as matice from './sheets/matrix.js';
import * as vety from './sheets/sentences.js';
import * as rozhovor from './sheets/conversation.js';
import * as dialog from './dialog/new-sentence.js';

const pohledy = {};
const listy = {};
let model = null, mapa = [], editovane = new Set();
let stavDialogu = null;

/* ---- překreslení ----------------------------------------------------
   Model se NEPOČÍTÁ tady — vyzvedne se z backendu. Zdroj pravdy sedí
   v Pythonu, prohlížeč je jen jeden ze dvou kanálů k témuž jádru. */
let poradi = new Map();
let cekaNaModel = null;

async function prepocitat() {
  const odpoved = await store.nactiPole(stav);
  model = prevzit(odpoved, { facts: D.data.facts, query: D.data.query });
  prekresli();
}

function prekresli() {
  if (!model) return;
  ['f', 'q'].forEach(k => korpus.prekresli(pohledy[k], model[k], model.slovnik, handlery));
  defin.prekresli(listy.mapd, model, model.slovnik, mapa, akceMapy, poradi);
  prehled.prekresli(listy.mapp, model.slovnik, model, mapa, akceMapy);
  vert.prekresli(listy.vert, editovane, akceVertikal);
  matice.prekresli(listy.mx, editovane, akceVertikal);
  vety.prekresli(listy.vety, akceVet);
  vety.tabulkaVazeb(listy.vety, model.slovnik);
  rozhovor.prekresli(listy.dial, stavDialogu, akceDialogu);

  $('#tnF').textContent = D.data.facts.length;
  $('#tnQ').textContent = D.data.query.length;
  $('#tnM').textContent = mapa.length;
  $('#tnV').textContent = D.data.cols.length;
  $('#tnMx').textContent = editovane.size;
  $('#tnS').textContent = vety.pocetVet();
  $('#tnD').textContent = stavDialogu ? stavDialogu.znalost.cisla.tvrzeni : '';
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
/* Skládání otázky. Klik ve slovníku dotazů přidá slovo do vzoru, klik ve
   slovníku faktů přepne cíl. Překresluje se jen list definice — přepočítávat
   kvůli jednomu kliknutí celý model by bylo zbytečné. */
const znovuDefinici = async () => {
  /* Vektor složené otázky spočítá JÁDRO na backendu. Bez kotvy se neptáme —
     nemá se od čeho počítat offset. */
  const v = sklad.vzor;
  sklad.zapamatuj(v.kotva >= 0 && v.q.length
    ? await store.slozitVzor({ q: v.q, kotva: v.kotva, f: v.f }, stav)
    : null);
  defin.prekresli(listy.mapd, model, model.slovnik, mapa, akceMapy, poradi);
  poHrany();
};
const akceMapy = {
  klikSlovo: (k, form) => {
    if (k === 'q') sklad.pridejSlovo(form); else sklad.prepniCil(form);
    znovuDefinici();
  },
  kotva: form => { sklad.pridejKotvu(form); znovuDefinici(); },
  odeber: i => { sklad.odeberSlovo(i); znovuDefinici(); },
  odeberCil: form => { sklad.prepniCil(form); znovuDefinici(); },
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
    store.ulozData(D.data).then(prepocitat);
    prekresli();
  },
  prepniAktivaci: (k, z, t, a) => {
    D.prepniAktivaci(k, z, t, a);
    store.ulozData(D.data).then(prepocitat);
    prekresli();
  },
};

/* Dialog. Stránka jen podá text a překreslí, co přišlo zpátky — mluvnice
   i odvozování sedí v jádře. */
const akceDialogu = {
  rozhodni: async druh => { stavDialogu = await store.rozhodniDialog(druh); prekresli(); },
};

async function posli(text) {
  if (!text.trim()) return;
  stavDialogu = await store.posliDialog(text);
  prekresli();
}

const akceVet = {
  smazVetu: (k, i) => {
    if (!confirm(`Smazat ${k === 'f' ? 'větu' : 'dotaz'} ${i + 1}?`)) return;
    D.smazVetu(k, i);
    stav.pin = null;
    store.ulozData(D.data).then(prepocitat);
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
      if (prepocitatMapu) { sklad.vycisti(); await nactiMapu(); }
      await prepocitat();
    };
  });
}

/* Mapování se zakládá LÍNĚ: první otevření dvojice poloměrů dostane
   předvyplněná data, další už si žije vlastním životem. */
async function nactiMapu() {
  const klic = store.klicMapy(stav.R);
  const nal = await store.nactiMapu(klic);
  /* Store se zakládá LÍNĚ: první otevření dvojice poloměrů dostane
     předvyplněnou sadu z backendu, další už si žije vlastním životem. */
  mapa = nal ? nal.dvojice : [];
  if (nal && !nal.vlastni) await store.ulozMapu(klic, mapa);
}

/* ---- start ----------------------------------------------------------- */
export async function start() {
  bub.priprav();

  const zdroj = await store.nactiData();
  const vychozi = { cols: zdroj.vertikaly, facts: zdroj.korpusy.facts,
    query: zdroj.korpusy.query, mapa: [] };
  D.zapamatujVychozi(vychozi);
  D.nastav(vychozi);
  editovane = new Set(D.data.cols.filter(c => c.g === 'TYP' || c.g === 'PTÁ' || c.g === 'VLASTNÍ')
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
  listy.dial = rozhovor.postavList();
  ['mapd', 'mapp', 'vert', 'mx', 'vety', 'dial']
    .forEach(x => hlavni.appendChild(listy[x]));
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
    if (!sklad.hotovy()) return;
    mapa.push(sklad.doZaznamu());
    store.ulozMapu(store.klicMapy(stav.R), mapa);
    sklad.vycisti();
    prekresli();
  };
  $('#bZrus').onclick = () => { sklad.vycisti(); znovuDefinici(); };

  /* Filtr palety: text a výběr otázky. Slovník je společný a roste s každou
     zadanou otázkou, takže bez filtru je paleta brzo nepřehledná. */
  listy.mapd.addEventListener('input', e => {
    if (e.target.classList.contains('hledej')) {
      defin.filtr[e.target.dataset.k] = e.target.value;
      znovuDefinici();
    }
  });
  listy.mapd.addEventListener('change', e => {
    if (e.target.classList.contains('vybraVeta')) {
      defin.filtr.veta = +e.target.value;
      znovuDefinici();
    }
  });

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
    store.ulozData(D.data).then(prepocitat);
    $('#dnew').close();
    prekresli();
  };
  $('#bReset').onclick = () => {
    if (!confirm('Zahodit všechny změny v obou korpusech i vlastní vertikály '
      + 'a vrátit výchozí data? Mapování zůstane.')) return;
    D.naVychozi();
    editovane = new Set(D.data.cols.filter(c => c.g === 'TYP' || c.g === 'PTÁ' || c.g === 'VLASTNÍ')
      .map(c => c.a));
    stav.pin = null;
    store.ulozData(D.data).then(prepocitat);
    prekresli();
  };
  $('#dSend').onclick = () => { const i = $('#dText'); posli(i.value); i.value = ''; };
  $('#dText').onkeydown = e => {
    if (e.key === 'Enter') { e.preventDefault(); $('#dSend').click(); }
  };
  $('#dUkazka').onclick = async () => {
    /* Po jedné a po sobě: druhá věta staví na tom, co udělala první. */
    for (const veta of rozhovor.UKAZKA) await posli(veta);
  };
  $('#dZapomen').onclick = async () => {
    if (!confirm('Zapomenout všechno, co se systém naučil rozhovorem? '
      + 'Typový svaz z Wikidat zůstane.')) return;
    stavDialogu = await store.zapomenDialog();
    prekresli();
  };
  addEventListener('resize', poHrany);

  /* Nakresli hned z místních dat, ať je něco vidět, a teprve pak se ptej
     backendu. Druhé nactiMapu() je podstatné: to první běželo dřív, než se
     vědělo, jestli server existuje, takže sáhlo jen do prohlížeče. */
  prepniList(stav.sheet);
  await nactiMapu();
  stavDialogu = await store.nactiDialog();
  await prepocitat();
}

function pridejVertikalu() {
  const a = $('#vName').value.trim(), g = $('#vGrp').value;
  const chyba = D.pridejVertikalu(a, g);
  $('#vWarn').textContent = chyba || '';
  if (chyba) return;
  editovane.add(a);
  $('#vName').value = '';
  store.ulozData(D.data).then(prepocitat);
  prekresli();
}

start();
