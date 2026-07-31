/* Hrany mezi panely. SVG leží přes plátno a nechytá myš.

   Z prázdných řádků se hrany do <empty> NEkreslí: při r=8 by jich byly
   stovky a plátno by pod nimi zmizelo. Rozsvítí se až najetím na <empty>. */

const NS = 'http://www.w3.org/2000/svg';

export function stred(plocha, prvek, strana) {
  const b = prvek.getBoundingClientRect(), s = plocha.getBoundingClientRect();
  return [(strana === 'r' ? b.right : b.left) - s.left, b.top - s.top + b.height / 2];
}

export function kresli(sv, a, b, trida, data) {
  const p = document.createElementNS(NS, 'path');
  const dx = (b[0] - a[0]) * 0.5;
  p.setAttribute('d', `M${a[0]},${a[1]}C${a[0] + dx},${a[1]} ${b[0] - dx},${b[1]} ${b[0]},${b[1]}`);
  if (trida) p.setAttribute('class', trida);
  Object.entries(data || {}).forEach(([k, v]) => (p.dataset[k] = v));
  sv.appendChild(p);
}

export function vycisti(sv, plocha) {
  const s = plocha.getBoundingClientRect();
  sv.setAttribute('viewBox', `0 0 ${s.width} ${s.height}`);
  sv.innerHTML = '';
  return s;
}

/* Rozestup sloupců. Pevná hodnota byla málo: na užším okně se panely
   sesypou k sobě a hrany se slijí. Bere se POLOVINA PRŮMĚRNÉ šířky panelu,
   a to bez pole — to je řádově širší a průměr by strhlo.

   Do toho vstupuje i VÝŠKA, protože ta určuje sklon hran: čím vyšší
   sloupec, tím strmější svazek a tím víc vodorovného místa potřebuje.
   Škáluje se odmocninou, ne přímo — panel šablon dotazů je přes dva tisíce
   pixelů vysoký a lineární vztah by utekl. */
export function rozestup(plocha) {
  const p = [...plocha.querySelectorAll('.panel')]
    .filter(e => !e.classList.contains('p-field'));
  if (!p.length) return;
  const w = p.reduce((n, e) => n + e.getBoundingClientRect().width, 0) / p.length;
  const h = Math.max(...p.map(e => e.getBoundingClientRect().height));
  const k = Math.sqrt(Math.min(h, 2400) / 600);
  plocha.style.setProperty('--bw',
    Math.round(Math.max(72, Math.min(180, 0.5 * w * k))) + 'px');
}

/** Řetěz pole → slovník → vazby → šablony pro jednu stranu. */
export function retez(sv, plocha, prvky, model, sdilena) {
  const okraj = prvky.pole.getBoundingClientRect().right
    - plocha.getBoundingClientRect().left;
  model.own.forEach(o => {
    const radek = prvky.rows.querySelector(`[data-row="${o.i}"]`);
    const lk = model.wordOf.get(o.i);
    const li = prvky.lex.querySelector(`[data-w="${lk.w}"]`);
    if (!radek || !li) return;
    const a = stred(plocha, radek, 'r');
    kresli(sv, [okraj, a[1]], stred(plocha, li, 'l'),
      sdilena(lk.t) ? 'heat' : '', { row: o.i, w: lk.w, t: lk.t });
  });
  model.links.forEach((L, n) => {
    const li = prvky.lex.querySelector(`[data-w="${L.w}"]`);
    const ln = prvky.lnk.querySelector(`[data-l="${n}"]`);
    const tl = prvky.tpl.querySelector(`[data-t="${L.t}"]`);
    const trida = sdilena(L.t) ? 'heat' : '';
    if (li && ln) kresli(sv, stred(plocha, li, 'r'), stred(plocha, ln, 'l'),
      trida, { w: L.w, t: L.t, l: n });
    if (ln && tl) kresli(sv, stred(plocha, ln, 'r'), stred(plocha, tl, 'l'),
      trida, { w: L.w, t: L.t, l: n });
  });
}
