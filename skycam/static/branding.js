'use strict';
// textContent and setAttribute keep operator text out of executable HTML.
(async () => {
  const response = await fetch('/api/branding');
  if (!response.ok) return;
  const brand = await response.json();
  window.stationBrand = Object.freeze(brand);
  if ((location.pathname === '/studio' || location.pathname.startsWith('/studio/'))) {
    const mode = await fetch('/api/release-mode').then(r => r.json());
    if (mode.offline) {
      const notice = document.createElement('p');
      notice.textContent = 'Offline preview. Controls are disabled; no live sources or programme output.';
      notice.style.cssText = 'padding:12px 20px;background:#fff1b8;color:#18232b;margin:0;font:600 16px sans-serif';
      document.body.prepend(notice);
      const disableWrites = () => document.querySelectorAll('button:not([data-preview-safe]),input:not([data-preview-safe]),select:not([data-preview-safe]),textarea:not([data-preview-safe])').forEach(el => { if (!el.disabled) el.disabled = true; });
      disableWrites();
      // Polling creates/re-enables controls after the initial page load.
      new MutationObserver(disableWrites).observe(document.body, {childList:true, subtree:true, attributes:true, attributeFilter:['disabled']});
    }
  }
  const replace = value => value.replace(/\[\[([a-z_]+)\]\]/g, (match, key) =>
    Object.hasOwn(brand, key) ? String(brand[key]) : match);
  const walk = document.createTreeWalker(document.documentElement, NodeFilter.SHOW_TEXT);
  for (let node = walk.nextNode(); node; node = walk.nextNode()) {
    if (!['SCRIPT', 'STYLE'].includes(node.parentElement?.tagName)) node.textContent = replace(node.textContent);
  }
  document.querySelectorAll('[title],[alt]').forEach(el => {
    for (const attr of ['title', 'alt']) if (el.hasAttribute(attr)) el.setAttribute(attr, replace(el.getAttribute(attr)));
  });
  document.documentElement.style.setProperty('--accent', brand.accent);
  document.documentElement.style.setProperty('--orange', brand.accent);
  if (brand.logo_asset) {
    document.querySelectorAll('.logo').forEach(el => {
      const img = document.createElement('img');
      img.src = '/api/branding/logo'; img.alt = brand.station_short;
      img.style.cssText = 'width:100%;height:100%;object-fit:contain';
      el.replaceChildren(img);
    });
  }
})();
