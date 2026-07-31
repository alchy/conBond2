/* Dialog — znalost se zadává větou, ne tabulkou.

   Prohlížeč tu nerozhoduje o ničem: pošle text a dostane zpátky, co se s ním
   stalo. Druh tvrzení, odvození i odmítnutí řeší jádro, protože zdroj pravdy
   sedí na backendu a stránka je jen jeden ze dvou kanálů.

   Tři odpovědi, ne dvě: `nevím` není výmluva. Pole je monotónní a chybějící
   hrana znamená, že se nikdo neptal, ne že odpověď je ne. */

import { el, esc } from '../util.js';

const ZNAKY = { podtrida: '⊂', instance: '∈', synonymum: '=', zapor: '≠' };
const POPIS = { podtrida: 'podtřída', instance: 'instance',
                synonymum: 'synonymum', zapor: 'zápor' };

export const UKAZKA = [
  'Kde se narodil Bohumil Hrabal?',
  'Krakatit je román.',
  'román je druh díla',
  '? Krakatit dílo',
  'Krakatit není báseň',
  '? Krakatit báseň',
];

export function postavList() {
  const rozhovor = el('div', { class: 'card rozhovor' }, [
    el('h2', {}, 'Rozhovor'),
    el('p', { class: 'hint', html:
      'Znalost se zadává větou. <b>X je druh Y</b> je podtřída, <b>X je Y</b> '
      + 'instance, <b>X je totéž co Y</b> synonymum, <b>X není Y</b> zápor. '
      + 'Otázka na vztah je <b>? X Y</b>, rodokmen <b>?? X</b>.<br>'
      + '<b>Kde / Kdy / Kolik</b> se ptá na <b>obsah korpusu</b> — odpoví pole '
      + 'a kandidáti se vypíšou vpravo.<br>Když si mluvnice není jistá, '
      + '<b>zeptá se</b>: „pes je savec" může být obojí a špatná hrana se šíří '
      + 'expanzí dál.' }),
    el('div', { class: 'prepis', id: 'dPrepis' }),
    el('div', { class: 'ptani', id: 'dPtani', hidden: '' }),
    el('div', { class: 'radek' }, [
      el('input', { type: 'text', id: 'dText', size: '46',
        placeholder: 'Krakatit je román.  ·  ? Krakatit dílo' }),
      el('button', { class: 'act', id: 'dSend' }, 'Řekni'),
    ]),
    el('div', { class: 'radek' }, [
      el('button', { class: 'lehke', id: 'dUkazka' }, 'Předvést na příkladu'),
      el('button', { class: 'lehke', id: 'dZapomen' }, 'Zapomenout naučené'),
    ]),
  ]);

  /* Kandidáti dostali místo vpravo, protože jich je hodně a jsou to ta
     zajímavá data. Šablona je abstrakce, která má kandidáty MATCHNOUT —
     vybrat z nich jednoho je jiná úloha, tak se ukazují všichni. */
  const kandidati = el('div', { class: 'card kandidati' }, [
    el('h2', {}, 'Kandidáti odpovědi'),
    el('p', { class: 'hint', html:
      'Otázka na obsah rozsvítí pole: <b>osoba</b> se hledá jako aktivace '
      + '<code>Ent=</code> (ve větě jako slovo většinou vůbec není — čeština '
      + 'podmět zahazuje), <b>sloveso</b> jako tvar ve slovníku. Průnik je '
      + 'pole odpovědi a tázací tvar řekne, jaký <b>druh</b> místa v něm '
      + 'hledat.' }),
    el('div', { class: 'akt', id: 'dAkt' }),
    el('div', { class: 'kseznam', id: 'dKand' }),
  ]);

  /* Znalost je sbalená: čte se občas, kdežto kandidáti pořád. */
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
    [el('div', { class: 'two' }, [rozhovor, kandidati]), znalost]);
}

/* ---- vykreslení ------------------------------------------------------ */
function radekPrepisu(z) {
  const trida = { tvrzeni: 'ok', otazka: 'dotaz', rodokmen: 'dotaz',
                  nejasnost: 'ptam', odmitnuto: 'ne', chyba: 'ne' }[z.druh] || '';
  /* U tvrzení je hrana už v odpovědi („přijato: X ⊂ Y") a chip by ji
     zopakoval slovo od slova. U otázky a nejasnosti přidá, jak se pojmy
     normalizovaly, takže tam smysl má. */
  const ukazHranu = z.hrana && z.hrana.levy && z.druh !== 'tvrzeni';
  const hrana = ukazHranu
    ? `<span class="hrana">${esc(z.hrana.levy)} <b>${esc(z.hrana.znak)}</b> `
      + `${esc(z.hrana.pravy)}</span>` : '';
  return `<div class="tah ${trida}"><div class="rekl">${esc(z.text)}</div>`
    + `<div class="rekl2">${esc(z.odpoved)}${hrana}</div></div>`;
}

export function prekresli(root, stav, akce) {
  if (!root || !stav) return;
  const prepis = root.querySelector('#dPrepis');
  prepis.innerHTML = stav.historie.length
    ? stav.historie.map(radekPrepisu).join('')
    : '<div class="tah prazdno">Zatím nic. Zkus „Krakatit je román."</div>';
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
    + `<span class="muted">${c.uzlu_celkem} uzlů i s podkladem</span>`;

  kresliKandidaty(root, stav.nalez);

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


/* ---- kandidáti -------------------------------------------------------- */
function kresliKandidaty(root, n) {
  const akt = root.querySelector('#dAkt');
  const seznam = root.querySelector('#dKand');
  if (!n) {
    akt.innerHTML = '';
    seznam.innerHTML = '<p class="hint">Zeptej se na obsah: '
      + '„Kde se narodil Bohumil Hrabal?"</p>';
    return;
  }
  const a = n.aktivace;
  const tvary = Object.entries(a.svitici).filter(([, k]) => k)
    .map(([t, k]) => `<i class="cip">${esc(t)} <b>${k}</b></i>`).join('');
  akt.innerHTML =
    (a.entita ? `<div class="r"><span>osoba</span><i class="cip ent">Ent=`
      + `${esc(a.entita)} <b>${a.vet_entity}</b></i></div>` : '')
    + (tvary ? `<div class="r"><span>tvary</span>${tvary}</div>` : '')
    + (a.nezname.length ? `<div class="r"><span>nesvítí</span>`
       + a.nezname.map(t => `<i class="cip pryc">${esc(t)}</i>`).join('') + '</div>' : '')
    + `<div class="r"><span>pole</span><i class="cip">${n.vet} vět</i>`
    + `<i class="cip">${esc(n.typ || '—')}</i>`
    + (a.siroko ? '<i class="cip pryc">sloveso nesedlo — celá osoba</i>' : '')
    + (n.znalost_pomohla ? '<i class="cip zn">pomohla znalost</i>' : '') + '</div>';

  seznam.innerHTML = n.kandidati.length
    ? `<div class="pocet">${n.kandidati.length} kandidátů</div>`
      + n.kandidati.map((k, i) => `<div class="kand${i ? '' : ' prvni'}">`
        + `<b>${esc(k.text)}</b><span class="vt">věta ${k.veta}</span>`
        + `<div class="ctx">${esc(k.kontext.slice(0, 150))}${k.kontext.length > 150 ? '…' : ''}</div>`
        + '</div>').join('')
    : '<p class="hint">V poli není nic toho druhu.</p>';
}
