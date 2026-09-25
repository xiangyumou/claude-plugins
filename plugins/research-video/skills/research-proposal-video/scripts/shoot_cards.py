#!/usr/bin/env python3
"""Screenshot HTML/CSS cards to PNG and check their layout before they reach the film.

The page is served from its own folder over local HTTP (relative images, fonts and data load
as in a browser). By default it must define `SCENES` (a list of card ids) and `render(id)`,
which draws one card; `--ids` and `--render` take other JS functions. After fonts load, each
card is checked for:

  outside-card    text that runs past the edge of its card (`--card`, default `.card`)
  off-screen      text outside the frame
  text-overlap    two separate text blocks drawn on top of each other
  crosses-line    text that a visible stroke (curve, axis, gridline) runs through, unless
                  something opaque (e.g. a label background) is drawn between them

An element (or an ancestor) with `data-allow-overlap` is exempt. The PNGs are written either
way; the exit status is 1 when a card has a problem, so it can gate a render. The browser's
own request for /favicon.ico is answered, so it does not show up as a console 404.

  python shoot_cards.py work/cards/cards.html work/cards/out
  python shoot_cards.py work/cards/cards.html work/cards/out_v2 fgr explain   # only these cards
  python shoot_cards.py deck.html out --render "id => show(id)" --ids "() => IDS" --scale 1
Needs Playwright (`pip install playwright && playwright install chromium`; an installed
Google Chrome is used when the bundled Chromium is missing).
"""
import argparse
import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

CHECK = r"""
({cardSel, tol}) => {
  const W = innerWidth, H = innerHeight, issues = [];
  const allowed = el => !!(el && el.closest('[data-allow-overlap]'));
  const visible = el => !el.checkVisibility || el.checkVisibility({opacityProperty: true, visibilityProperty: true});
  const inSvg = el => el instanceof SVGElement;
  // the block that owns a text node: its <text> in SVG, its nearest non-inline box in HTML
  const owner = el => {
    if (inSvg(el)) return el.closest('text') || el;
    while (el.parentElement && getComputedStyle(el).display.startsWith('inline')) el = el.parentElement;
    return el;
  };
  const label = el => {
    const t = (el.textContent || '').trim().replace(/\s+/g, ' ');
    return t.length > 40 ? t.slice(0, 37) + '...' : t;
  };
  const texts = [], ctx = document.createElement('canvas').getContext('2d');
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = walk.nextNode());) {
    const el = n.parentElement;
    if (!n.textContent.trim() || !el || ['SCRIPT', 'STYLE'].includes(el.tagName) || !visible(el)) continue;
    let rects;
    if (inSvg(el)) rects = [el.getBoundingClientRect()];
    else { const r = document.createRange(); r.selectNodeContents(n); rects = [...r.getClientRects()]; }
    // layout boxes span the font's full ascent+descent; shrink them to the glyphs actually drawn,
    // so a small label just above a very large number is not reported as overlapping it
    const cs = getComputedStyle(el); ctx.font = cs.font || `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const mt = ctx.measureText(n.textContent.trim()), fa = mt.fontBoundingBoxAscent, fd = mt.fontBoundingBoxDescent;
    rects = rects.filter(r => r.width > 0.5 && r.height > 0.5).map(r => {
      const k = r.height / (fa + fd || r.height), base = r.top + fa * k;
      const top = Math.max(r.top, base - mt.actualBoundingBoxAscent * k), bottom = Math.min(r.bottom, base + mt.actualBoundingBoxDescent * k);
      return bottom > top ? {left: r.left, right: r.right, top, bottom, width: r.width, height: bottom - top} : r;
    });
    if (rects.length) texts.push({el, own: owner(el), rects});
  }
  const seen = new Set(), add = (kind, el, detail) => {
    const key = kind + '|' + label(el) + '|' + detail;
    if (!seen.has(key)) { seen.add(key); issues.push({kind, text: label(owner(el)), detail}); }
  };
  for (const t of texts) {
    if (allowed(t.el)) continue;
    const card = t.el.closest(cardSel);
    const c = card && card.getBoundingClientRect();
    for (const r of t.rects) {
      if (r.left < -tol || r.top < -tol || r.right > W + tol || r.bottom > H + tol) add('off-screen', t.el, '');
      if (c) {
        const out = Math.max(c.left - r.left, c.top - r.top, r.right - c.right, r.bottom - c.bottom);
        if (out > tol) add('outside-card', t.el, `${Math.round(out)} px past the card edge`);
      }
    }
  }
  for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
    const a = texts[i], b = texts[j];
    if (a.own === b.own || a.own.contains(b.own) || b.own.contains(a.own) || allowed(a.el) || allowed(b.el)) continue;
    for (const p of a.rects) for (const q of b.rects) {
      const w = Math.min(p.right, q.right) - Math.max(p.left, q.left), h = Math.min(p.bottom, q.bottom) - Math.max(p.top, q.top);
      if (w > 2 && h > 2 && w * h > 0.25 * Math.min(p.width * p.height, q.width * q.height))
        add('text-overlap', a.el, `with "${label(b.own)}"`);
    }
  }
  // strokes running through text: sample each visible stroked shape and ask what is on top there
  const boxes = texts.filter(t => !allowed(t.el)).flatMap(t => t.rects.map(r => ({t, r})));
  for (const g of document.querySelectorAll('path, line, polyline, polygon, circle, ellipse, rect')) {
    const cs = getComputedStyle(g);
    if (cs.stroke === 'none' || parseFloat(cs.strokeWidth) <= 0 || !visible(g) || allowed(g) || !g.getTotalLength) continue;
    const m = g.getScreenCTM(); if (!m) continue;
    const len = g.getTotalLength(), step = Math.max(3, len / 1500);
    const hit = new Set();
    for (let l = 0; l <= len; l += step) {
      const p = g.getPointAtLength(l).matrixTransform(m);
      for (const {t, r} of boxes) {
        if (hit.has(t) || p.x < r.left + 1 || p.x > r.right - 1 || p.y < r.top + 2 || p.y > r.bottom - 2) continue;
        const top = document.elementsFromPoint(p.x, p.y).find(e => !(e.tagName === 'text' || e.tagName === 'tspan' || e === t.el || t.el.contains(e) || e.contains(t.el)));
        if (top === g) { hit.add(t); add('crosses-line', t.el, `<${g.tagName}> runs through it`); }
      }
    }
  }
  return issues;
}
"""


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.split("?")[0] == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", type=Path)
    ap.add_argument("out", type=Path, help="folder for <id>.png")
    ap.add_argument("ids", nargs="*", help="cards to shoot (default: all from --ids)")
    ap.add_argument("--render", default="id => render(id)", help="JS function that draws one card")
    ap.add_argument("--ids", dest="ids_js", default="() => SCENES", help="JS function returning all card ids")
    ap.add_argument("--card", default=".card", help="CSS selector of the panels text must stay inside")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--scale", type=float, default=1.25, help="device scale factor (PNG = size x scale)")
    ap.add_argument("--wait", type=int, default=400, help="ms to wait after render() before checking")
    ap.add_argument("--tolerance", type=float, default=1.0, help="px of overflow ignored")
    ap.add_argument("--no-check", action="store_true", help="only take the screenshots")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    root = args.html.resolve().parent
    args.out.mkdir(parents=True, exist_ok=True)
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    problems = 0
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception:
                browser = p.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": args.width, "height": args.height},
                                    device_scale_factor=args.scale)
            errors = []
            page.on("console", lambda m: m.type == "error" and errors.append(m.text))
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{srv.server_address[1]}/{args.html.name}", wait_until="networkidle")
            ids = args.ids or page.evaluate(f"({args.ids_js})()")
            for card_id in ids:
                page.evaluate(f"id => ({args.render})(id)", card_id)
                page.evaluate("document.fonts.ready.then(() => 0)")
                page.wait_for_timeout(args.wait)
                page.screenshot(path=str(args.out / f"{card_id}.png"))
                issues = [] if args.no_check else page.evaluate(CHECK, {"cardSel": args.card, "tol": args.tolerance})
                problems += bool(issues)
                print(card_id, "ok" if not issues else f"{len(issues)} problem(s)")
                for it in issues:
                    print(f"  {it['kind']}: \"{it['text']}\" {it['detail']}".rstrip())
            browser.close()
    finally:
        srv.shutdown()
    if errors:
        print("page errors:", json.dumps(errors, ensure_ascii=False))
    if problems:
        print(f"{problems} card(s) need a layout fix (screenshots written to {args.out})")
    sys.exit(1 if problems or errors else 0)


if __name__ == "__main__":
    main()
