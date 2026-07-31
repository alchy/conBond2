/* Dialog — rozhovor jako u chatu: otázka, odpověď, a detail až na vyžádání.

   Prohlížeč tu nerozhoduje o ničem: pošle text a dostane zpátky, co se s ním
   stalo. Druh tvrzení, odvození i odmítnutí řeší jádro, protože zdroj pravdy
   sedí na backendu a stránka je jen jeden ze dvou kanálů.

   PROČ JE DETAIL SCHOVANÝ, ALE NE ZAHOZENÝ. Odpověď je jedno slovo, kdežto
   cesta k ní je pět řádků: která osoba se rozsvítila, které tvary, jak
   široké vyšlo pole a kolik v něm bylo kandidátů. Číst to u každého tahu je
   otrava; nemít to k dispozici znamená věřit stroji na slovo. Proto má každý
   tah vlastní `<details>` — zavřený, ale úplný.

   Tři odpovědi, ne dvě: `nevím` není výmluva. Pole je monotónní a chybějící
   hrana znamená, že se nikdo neptal, ne že odpověď je ne. */

import { el, esc } from '../util.js';

const ZNAKY = { podtrida: '⊂', instance: '∈', synonymum: '=', zapor: '≠' };
const POPIS = { podtrida: 'podtřída', instance: 'instance',
                synonymum: 'synonymum', zapor: 'zápor' };

const cislo = x => new Intl.NumberFormat('cs').format(x);

export const UKAZKA = [
  'Kdo je Bohumil Hrabal?',
  'Kde se narodil?',          // bez jména — vezme téma z předchozího tahu
  'Kdy zemřel?',
  'Kdo je Karel Čapek?',      // téma se přepne
  'Kde se narodil?',
  'Kdy se narodil Sherlock Holmes?',   // téma NESMÍ zachránit cizí jméno
];

export function postavList() {
  const chat = el('div', { class: 'card chat' }, [
    el('div', { class: 'prepis', id: 'dPrepis' }),
    el('div', { class: 'ptani', id: 'dPtani', hidden: '' }),
    el('div', { class: 'vstup' }, [
      el('input', { type: 'text', id: 'dText', autocomplete: 'off',
        placeholder: 'Kdo je Alois Jirásek?   ·   Krakatit je román.' }),
      el('button', { class: 'act', id: 'dSend' }, 'Zeptat se'),
    ]),
    el('div', { class: 'pod' }, [
      el('button', { class: 'lehke', id: 'dUkazka' }, 'Předvést na příkladech'),
      el('button', { class: 'lehke', id: 'dZapomen' }, 'Zapomenout naučené'),
      el('span', { class: 'napoveda', html:
        '<b>Kdo · Co · Kde · Kdy · Kolik</b> se ptá korpusu &nbsp;·&nbsp; '
        + '<b>X je druh Y</b> učí vztah &nbsp;·&nbsp; <b>? X Y</b> se ptá na vztah' }),
    ]),
  ]);

  /* Znalost je sbalená: čte se občas, kdežto rozhovor pořád. */
  const znalost = el('details', { class: 'card znalost', id: 'dZnalost' }, [
    el('summary', {}, [el('b', {}, 'Co systém ví'),
      el('span', { class: 'cisla', id: 'dCisla' })]),
    el('p', { class: 'hint', html:
      'Jen hrany <b>z tohohle rozhovoru</b>. Typový svaz z Wikidat je pod tím '
      + 'jako podklad a odvozuje se přes něj taky — proto „Krakatit je dílo" '
      + 'vyjde i tehdy, když se o díle nikdo nezmínil.' }),
    el('div', { class: 'hrany', id: 'dHrany' }),
    el('div', { class: 'pojmy', id: 'dPojmy' }),
  ]);

  return el('section', { class: 'sheet', id: 's-dial', hidden: '' },
    [chat, znalost]);
}

/* ---- jeden tah ------------------------------------------------------- */
function odpovedTahu(z) {
  /* U otázky na obsah je ODPOVĚĎ to slovo, ne popis pole. Popis patří do
     detailu — jinak se to hlavní ztratí mezi čísly. */
  if (z.druh === 'obsah') {
    return z.nalez && z.nalez.odpoved
      ? { text: z.nalez.odpoved, trida: 'ok' }
      : { text: z.odpoved, trida: 'nevim' };
  }
  const trida = { tvrzeni: 'ok', otazka: 'ok', rodokmen: 'ok',
                  nejasnost: 'ptam', odmitnuto: 'ne', chyba: 'ne' }[z.druh] || '';
  return { text: z.odpoved, trida };
}

function detailTahu(z) {
  const kusy = [];
  const cip = (t, c = '') => `<i class="cip ${c}">${esc(t)}</i>`;
  if (z.nalez) {
    const a = z.nalez.aktivace;
    const r = [];
    if (a.entita) {
      /* „z tématu" je podstatné: odpověď na otázku bez jména se opírá
         o předchozí tah, ne o to, co je v ní napsané. */
      r.push('<div class="r"><span>osoba</span>'
        + `<i class="cip ent">Ent=${esc(a.entita)} <b>${a.vet_entity}</b></i>`
        + (a.z_tematu ? cip('z tématu rozhovoru', 'zn') : '') + '</div>');
    }
    const tvary = Object.entries(a.svitici).filter(([, k]) => k)
      .map(([t, k]) => `<i class="cip">${esc(t)} <b>${k}</b></i>`).join('');
    if (tvary) r.push(`<div class="r"><span>tvary</span>${tvary}</div>`);
    if (a.nezname.length) {
      r.push('<div class="r"><span>nesvítí</span>'
        + a.nezname.map(t => cip(t, 'pryc')).join('') + '</div>');
    }
    r.push('<div class="r"><span>pole</span>'
      + cip(cislo(z.nalez.vet) + ' vět') + cip(z.nalez.typ || '—')
      + (a.siroko ? cip('širší — něco se nepotkalo', 'pryc') : '')
      + (z.nalez.znalost_pomohla ? cip('pomohla znalost', 'zn') : '') + '</div>');
    kusy.push(`<div class="akt">${r.join('')}</div>`);

    const k = z.nalez.kandidati;
    if (k.length) {
      if (k.length > 1) kusy.push(`<div class="pocet">${k.length} kandidátů</div>`);
      kusy.push(k.map((x, i) =>
        `<div class="kand${i ? '' : ' prvni'}"><b>${esc(x.text)}</b>`
        + `<span class="vt">věta ${x.veta}</span>`
        + `<div class="ctx">${esc(x.kontext.slice(0, 170))}`
        + `${x.kontext.length > 170 ? '…' : ''}</div></div>`).join(''));
    }
  }
  /* U tvrzení je hrana už v odpovědi („přijato: X ⊂ Y"), jinde přidá, jak se
     pojmy normalizovaly. */
  if (z.hrana && z.hrana.levy && z.druh !== 'tvrzeni') {
    kusy.push('<div class="akt"><div class="r"><span>hrana</span>'
      + `<i class="cip">${esc(z.hrana.levy)} <b>${esc(z.hrana.znak)}</b> `
      + `${esc(z.hrana.pravy)}</i></div></div>`);
  }
  return kusy.join('');
}

function tah(z) {
  const o = odpovedTahu(z);
  const d = detailTahu(z);
  return '<div class="tah">'
    + `<div class="ja">${esc(z.text)}</div>`
    + `<div class="on ${o.trida}">${esc(o.text)}</div>`
    + (d ? `<details class="proc"><summary>jak k tomu došel</summary>${d}</details>`
         : '')
    + '</div>';
}

/* ---- vykreslení ------------------------------------------------------ */
export function prekresli(root, stav, akce) {
  if (!root || !stav) return;
  const prepis = root.querySelector('#dPrepis');
  prepis.innerHTML = stav.historie.length
    ? stav.historie.map(tah).join('')
    : '<div class="prazdno">Zeptej se korpusu — <b>Kdo je Alois Jirásek?</b>'
      + ' — nebo ho nauč vztah: <b>Krakatit je román.</b></div>';
  prepis.scrollTop = prepis.scrollHeight;

  /* Nejasnost blokuje další vstup — nedořešená hrana by se ztratila. */
  const ptani = root.querySelector('#dPtani');
  ptani.hidden = !stav.ceka;
  if (stav.ceka) {
    ptani.innerHTML =
      '<button class="act" data-r="podtrida">je to DRUH</button>'
      + '<button class="act" data-r="instance">je to KONKRÉTNÍ věc</button>'
      + '<button class="lehke" data-r="preskocit">přeskočit</button>';
    ptani.onclick = e => {
      if (e.target.dataset.r) akce.rozhodni(e.target.dataset.r);
    };
  }
  root.querySelector('#dText').disabled = stav.ceka;
  root.querySelector('#dSend').disabled = stav.ceka;

  const c = stav.znalost.cisla;
  root.querySelector('#dCisla').innerHTML =
    `<span><b>${c.tvrzeni}</b> tvrzení</span><span><b>${c.pojmy}</b> pojmů</span>`
    + `<span><b>${c.zapory}</b> záporů</span><span><b>${c.synonyma}</b> synonym</span>`
    + `<span class="muted">${cislo(c.uzlu_celkem)} uzlů i s podkladem</span>`;

  root.querySelector('#dHrany').innerHTML = stav.znalost.hrany.length
    ? stav.znalost.hrany.map(h =>
      `<div class="hr ${esc(h.druh)}"><span class="lv">${esc(h.levy)}</span>`
      + `<span class="zn">${esc(ZNAKY[h.druh] || h.znak)}</span>`
      + `<span class="pv">${esc(h.pravy)}</span>`
      + `<span class="dr">${esc(POPIS[h.druh] || h.druh)}</span></div>`).join('')
    : '<p class="hint">Žádná hrana z dialogu.</p>';

  /* Rodokmen ukazuje, co dělá expanze — bez něj by nebylo poznat, že
     odpověď „ano" přišla přes dva skoky, ne z přímé hrany. */
  root.querySelector('#dPojmy').innerHTML = stav.znalost.pojmy
    .filter(p => p.predci.length)
    .map(p => `<div class="rod"><b>${esc(p.jmeno)}</b> ⊂ `
      + p.predci.map(x => esc(x)).join(', ') + '</div>').join('');
}
