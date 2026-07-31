/* Kanál k jádru. Zdroj pravdy sedí v Pythonu na backendu — prohlížeč si
   model VYZVEDNE, nepočítá ho. Proto v js/ žádné jádro není.

   Zrcadlení dat do localStorage tu dřív bylo, ale s backendem jako zdrojem
   pravdy by to byla druhá pravda navíc. V prohlížeči zůstává jen nastavení
   pohledu (js/state.js) — to data nejsou. */

export const stavSpojeni = { online: false };

async function zavolej(cesta, volby) {
  try {
    const r = await fetch(cesta, volby);
    stavSpojeni.online = true;
    return r;
  } catch (e) {
    stavSpojeni.online = false;
    return null;
  }
}

/** Parametry pohledu do dotazu. Poloměry jsou dva a smí se lišit. */
const parametry = st => new URLSearchParams({
  rf: st.R.f, rq: st.R.q,
  syrove: st.punct ? 1 : 0,
  stred: st.cIn ? 1 : 0,
  typy: st.typyOn ? 1 : 0,
}).toString();

export const klicMapy = R => 'q' + R.q + 'f' + R.f;

/** Vertikály a oba korpusy. Stačí jednou, pak si je prohlížeč drží. */
export async function nactiData() {
  const r = await zavolej('/api/data', { cache: 'no-store' });
  if (!r || !r.ok) throw new Error('backend neodpovídá — běží python3 -m server?');
  return r.json();
}

export async function ulozData(data) {
  await zavolej('/api/data', {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      vertikaly: data.cols,
      korpusy: { facts: data.facts, query: data.query },
    }),
  });
}

/** Model pro dané nastavení: rozvržení řádků, šablony, vazby, slovník. */
export async function nactiPole(st) {
  const r = await zavolej('/api/field?' + parametry(st), { cache: 'no-store' });
  if (!r || !r.ok) throw new Error('backend nedal model');
  return r.json();
}

/** Vektor složené otázky — skládá ho jádro, ne prohlížeč. */
export async function slozitVzor(vzor, st) {
  const r = await zavolej('/api/compose?' + parametry(st), {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(vzor),
  });
  return r && r.ok ? r.json() : null;
}

/* Mapování má vlastní store pro KAŽDOU DVOJICI poloměrů: šablony dotazů
   závisí na r_q, šablony faktů na r_f, a ta dvě r se smí lišit. Jeden
   společný store by tvrdil, že mapování z r=1 platí i pro r=4. */
/* Backend vrátí i to, jestli je store vlastní, nebo se ještě sahá po
   výchozí sadě. Dřív se tu na 404 zakládalo PRÁZDNÉ mapování a předvyplněné
   dvojice se ztratily. */
export async function nactiMapu(klic) {
  const r = await zavolej('/api/mappings/' + klic, { cache: 'no-store' });
  if (!r || !r.ok) return null;
  return r.json();
}

export async function ulozMapu(klic, seznam) {
  await zavolej('/api/mappings/' + klic, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(seznam),
  });
}

/** Rozbor věty lokálním UDPipe přes backend. */
export async function rozeber(veta) {
  const r = await zavolej('/api/parse', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: veta }),
  });
  if (!r) return { chyba: 'backend neběží — rozbor je jen přes něj' };
  const o = await r.json();
  return r.ok ? o : { chyba: o.chyba || `rozbor selhal (HTTP ${r.status})` };
}
