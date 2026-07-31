/* Drobnosti, které potřebuje víc bloků. Nic víc sem nepatří — jakmile by
   tenhle soubor začal umět něco oborového, je to znamení, že to má vlastní
   místo. */

export const $ = (s, kde = document) => kde.querySelector(s);
export const $$ = (s, kde = document) => [...kde.querySelectorAll(s)];

export const esc = s => String(s).replace(/[&<>"]/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* 1 slot · 2 sloty · 5 slotů — počítaný tvar se v češtině láme na 1 a na 5. */
export const sklon = (n, a, b, c) => n + ' ' + (n === 1 ? a : (n >= 2 && n <= 4 ? b : c));

/** Věta jako text, s interpunkcí přisazenou k předchozímu slovu. */
export const vetaText = (vety, i) =>
  vety[i].map(t => t.form).join(' ').replace(/ ([,.;:!?])/g, '$1');

/** Vytvoří prvek: el('div', {class:'x'}, 'text' | [děti]) */
export function el(jmeno, atr = {}, obsah = null) {
  const e = document.createElement(jmeno);
  Object.entries(atr).forEach(([k, v]) => {
    if (k === 'class') e.className = v;
    else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on')) e[k] = v;
    else if (k.startsWith('data-')) e.setAttribute(k, v);
    else e.setAttribute(k, v);
  });
  if (typeof obsah === 'string') e.textContent = obsah;
  else if (Array.isArray(obsah)) obsah.forEach(d => d && e.appendChild(d));
  return e;
}
