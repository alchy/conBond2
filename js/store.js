/* Ukládání. Backend je volitelný — když neběží, jede se na localStorage.
   Zápis jde vždy do OBOU, aby se práce neztratila, když server spadne.

   MAPOVÁNÍ MÁ VLASTNÍ STORE PRO KAŽDOU DVOJICI POLOMĚRŮ. Šablony dotazů
   závisí na r_q, šablony faktů na r_f, a ta dvě r se smí lišit. Jeden
   společný store by tvrdil, že mapování z r=1 platí i pro r=4 — a to není
   pravda, je to jiné rozlišení téhož textu. */

const KLIC_STAV = 'pole2/state';
const KLIC_MAPA = 'pole2/map/';

export const stavSpojeni = { online: false };
export const klicMapy = R => 'q' + R.q + 'f' + R.f;

async function zkusApi(cesta, volby) {
  try { return await fetch(cesta, volby); }
  catch (e) { stavSpojeni.online = false; return null; }
}

/** Ozve se backendu. Vrací uložený stav, nebo null (i když server běží
    a je jen prázdný — to pozná podle stavSpojeni.online). */
export async function ozviSe() {
  const r = await zkusApi('/api/state', { cache: 'no-store' });
  if (!r) return null;
  stavSpojeni.online = true;              // odpověděl, tedy běží
  if (r.ok) {
    const s = await r.json();
    if (s && Array.isArray(s.cols)) return s;
  }
  return null;                            // 404 = běží, jen ještě nic nemá
}

export function stavZProhlizece(vychoziQuery) {
  try {
    const s = localStorage.getItem(KLIC_STAV);
    if (!s) return null;
    const d = JSON.parse(s);
    if (d && Array.isArray(d.cols) && Array.isArray(d.facts)) {
      if (!Array.isArray(d.query)) d.query = vychoziQuery;
      return d;
    }
  } catch (e) { /* prázdno */ }
  return null;
}

export function ulozStav(data) {
  const telo = { cols: data.cols, facts: data.facts, query: data.query };
  try { localStorage.setItem(KLIC_STAV, JSON.stringify(telo)); } catch (e) { /* prázdno */ }
  if (stavSpojeni.online) {
    zkusApi('/api/state', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(telo),
    });
  }
}

/* Vrací i ZDROJ, ne jen seznam. Bez toho nešlo rozeznat „server ten store
   ještě nemá" od „nikde nic není", a práce udělaná offline by se při prvním
   spuštění backendu přepsala předvyplněnými daty. */
export async function nactiMapu(klic) {
  if (stavSpojeni.online) {
    const r = await zkusApi('/api/maps/' + klic, { cache: 'no-store' });
    if (r && r.ok) return { list: await r.json(), zdroj: 'api' };
    // 404 = store na serveru zatím není; NEkončíme, zkusíme prohlížeč
  }
  try {
    const s = localStorage.getItem(KLIC_MAPA + klic);
    if (s) return { list: JSON.parse(s), zdroj: 'local' };
  } catch (e) { /* prázdno */ }
  return null;
}

export function ulozMapu(klic, seznam) {
  try { localStorage.setItem(KLIC_MAPA + klic, JSON.stringify(seznam)); }
  catch (e) { /* prázdno */ }
  if (stavSpojeni.online) {
    zkusApi('/api/maps/' + klic, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(seznam),
    });
  }
}

/** Rozbor věty lokálním UDPipe přes backend. Bez backendu to nejde. */
export async function rozeber(veta) {
  const r = await zkusApi('/api/parse', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: veta }),
  });
  if (!r) return { chyba: 'backend neběží — rozbor je jen přes něj' };
  const o = await r.json();
  return r.ok ? o : { chyba: o.chyba || ('rozbor selhal (HTTP ' + r.status + ')') };
}
