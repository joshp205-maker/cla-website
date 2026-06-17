#!/usr/bin/env python3
"""
Reusable CLA-report panel capture + anonymizer for the /sample page.

Captures real CLA/RNR report panels at retina (deviceScaleFactor=2), applies the
LOCKED anonymization recipe (brand/location/themed-label scrub, Chart.js relabel +
recolor to the site palette), and saves a PNG into public/shots/.

Palette: periwinkle #7d8fb8 / deep #5a6d9a ; subject accent orange #e85d1c.

Usage:
  python3 tools/capture_cla.py sentiment   # re-capture Brand-Y guest-sentiment chart

Each capture is a function below so the recipe per panel is explicit and auditable.
Always prints the post-anonymization label set so leaks can be eyeballed before save.
"""
import sys, re, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHOTS = ROOT / "public" / "shots"
RNR_URL = "https://rnr-birmingham-colonnade-al.netlify.app/"
BCO_URL = "https://bco-ft-lauderdale-957-fl.netlify.app/"

# Canonical RNR comp -> letter map, anchored to guest-rating rank so EVERY RNR
# shot uses the same letters (Comp A=5★ ... Comp K=3.9★; subject excluded).
RNR_COMP_MAP = {
    "Sushi Avenue": "A",
    "Nori Thai and Sushi": "B", "Nori Thai": "B",
    "The Ono Poke": "C", "Ono Poke": "C",
    "Surin 280": "D", "Surin": "D",
    "Blue Sushi Sake Grill": "E", "Blue Sushi (Unagi Nigiri x4 approx)": "E", "Blue Sushi": "E",
    "P.F. Chang's": "F", "P.F. Chang": "F", "PF Chang's": "F", "PF Chang": "F",
    "Eating Time Chinese Food": "G", "Eating Time": "G",
    "Kyuramen x TBaar - Birmingham": "H", "Kyuramen x TBaar": "H", "Kyuramen": "H",
    "Ginza Sushi & Korean BBQ": "I", "Ginza Sushi": "I", "Ginza": "I",
    "Maki Fresh — Georgia Birmingham": "J", "Maki Fresh — Birmingham": "J", "Maki Fresh": "J",
    "Kobe Japanese Steak House & Sushi Bar": "K", "Kobe": "K",
}

# Canonical B&Co (Brand-X) comp -> letter map, by guest-rating rank (subject excluded,
# pre-opening). Used across all Brand-X shots.
BCO_COMP_MAP = {
    "Goldberg's Bagels FL": "A", "Goldberg's Bagels": "A", "Goldberg's": "A",
    "Bagel Snack": "B",
    "Pomperdale Famous New York Deli": "C", "Pomperdale": "C",
    "NY Deli": "D",
    "Chesapeake Bagel Bakery": "E", "Chesapeake": "E",
    "Einstein Bros. Bagels": "F", "Einstein Bros": "F", "Einstein": "F",
    "Boston Bagel Cafe": "G", "Boston Bagel": "G",
    "Capital Bagel": "H",
    "Panera Bread": "I", "Panera": "I",
}

PERIWINKLE = "#7d8fb8"
PERIWINKLE_DEEP = "#5a6d9a"
ORANGE = "#e85d1c"
CANVAS = "#fefdfa"

# Identity tokens that must NEVER survive into a saved panel. Cuisine words
# (sushi/bagel/ramen) are NOT leaks — only brand, location, comp names, themed
# vocabulary, and source URLs are masked.
LEAK_TOKENS = [
    # subject brand
    "rock n roll", "rnr",
    # RNR comp names
    "surin", "ginza", "kobe", "maki fresh", "kyuramen", "nori thai", "blue sushi",
    "pf chang", "p.f. chang", "ono poke", "eating time", "sushi avenue", "tbaar",
    # locations
    "birmingham", "hoover", "mountain brook", "vestavia", "huntsville", "colonnade",
    "alabama", "fort lauderdale", "ft lauderdale", "lauderdale", "coral ridge", "broward",
    # RNR themed vocabulary
    "setlist", "headliner", "crowd review", "encore", "backstage", "amplified",
    # B&Co comps (filled in as captured)
    "einstein", "panera", "dunkin",
]
# Source URLs are a leak class of their own.
URL_RE = re.compile(r"\b[a-z0-9.-]+\.(com|net|org)\b", re.I)

def scan_leaks(label):
    low = label.lower()
    hits = [t for t in LEAK_TOKENS if t in low]
    for m in URL_RE.findall(label):
        hits.append("url")
    return list(dict.fromkeys(hits))


def capture_sentiment(page):
    """Brand-Y (operating, RNR) guest-sentiment leaderboard, left-aligned labels."""
    page.goto(RNR_URL, wait_until="networkidle")
    page.click('.tab-nav-tab[data-tab="operations"]')
    page.wait_for_function(
        "() => { const c = (window.Chart && Chart.getChart) ? Chart.getChart('chart_sentiment') : null;"
        " return c && c.canvas && c.canvas.height > 0; }"
    )

    result = page.evaluate(r"""() => {
      const PERI='#7d8fb8', PERID='#5a6d9a', ORANGE='#e85d1c';
      const chart = Chart.getChart('chart_sentiment');
      const subjIdx = chart.data.labels.findIndex(l => /Rock\s*N\s*Roll|RNR/i.test(l));
      const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
      let ci = 0;
      const newLabels = chart.data.labels.map((l, i) => {
        const m = String(l).match(/\(([\d.]+)★\s*\/\s*([\d,]+)\)/);
        const tail = m ? `${m[1]}★ · ${m[2]}` : '';
        if (i === subjIdx) return `Concept X   ${tail}`;
        return `Comp ${LETTERS[ci++]}   ${tail}`;
      });
      chart.data.labels = newLabels;
      const ds = chart.data.datasets[0];
      // bars fade lightest (highest-rated, top) -> darkest (worst, bottom); subject orange.
      // labels are already sorted rating-descending, so index maps straight to the ramp.
      const n = newLabels.length;
      const ramp = (t) => {            // t: 0 = light (best) .. 1 = dark (worst)
        const LT = [196, 206, 226], DK = [60, 74, 112];
        const h = (a, b) => ('0' + Math.round(a + (b - a) * t).toString(16)).slice(-2);
        return '#' + h(LT[0], DK[0]) + h(LT[1], DK[1]) + h(LT[2], DK[2]);
      };
      ds.backgroundColor = newLabels.map((_, i) => i === subjIdx ? ORANGE : ramp(n <= 1 ? 0 : i / (n - 1)));
      ds.borderColor = ds.backgroundColor.slice();
      ds.borderWidth = 0;
      // axis: left-align category labels (far side); darker + larger so scores read clearly
      chart.options.scales.y.ticks.crossAlign = 'far';
      chart.options.scales.y.ticks.color = newLabels.map((_, i) => i === subjIdx ? ORANGE : '#2a2f3a');
      chart.options.scales.y.ticks.font = (c) => ({
        family: "monospace", size: 13, weight: c.index === subjIdx ? '700' : '500'
      });
      if (chart.options.scales.y.grid) chart.options.scales.y.grid.display = false;
      if (chart.options.scales.x && chart.options.scales.x.ticks) {
        chart.options.scales.x.ticks.color = PERID;  // grid recolor skipped (breaks Chart grid obj)
      }
      if (chart.options.plugins) {
        if (chart.options.plugins.legend) chart.options.plugins.legend.display = false;
        if (chart.options.plugins.title) chart.options.plugins.title.display = false;
        if (chart.options.plugins.tooltip) chart.options.plugins.tooltip.enabled = false;
        if (chart.options.plugins.datalabels) chart.options.plugins.datalabels.color = PERID;
      }
      chart.options.animation = false;
      // deterministic layout: fixed height + no aspect-ratio so bars & ticks
      // share ONE vertical scale (lazy-canvas otherwise diverges -> off-by-one)
      chart.options.maintainAspectRatio = false;

      // frame the canvas wrapper for a clean capture
      const wrap = chart.canvas.parentElement;
      wrap.id = 'cap-target';
      wrap.style.cssText = 'background:#fefdfa;padding:26px 30px 22px;width:980px;height:520px;'
        + 'box-sizing:border-box;border:1px solid #e6e0d4;';
      chart.resize();
      chart.update();
      return { labels: newLabels, subjIdx };
    }""")

    page.wait_for_timeout(350)
    # second settle: re-fit bars to the final scale so alignment is exact
    page.evaluate("() => { const c = Chart.getChart('chart_sentiment'); c.resize(); c.update(); }")
    page.wait_for_timeout(250)
    SHOTS.mkdir(parents=True, exist_ok=True)
    out = SHOTS / "module-04-sentiment.png"
    page.locator('#cap-target').screenshot(path=str(out))
    return out, result["labels"]


# Neutral table palette to match the site / Brand-X shots (cream rows, navy header).
NEUTRAL_TABLE_CSS = """
#cap-target, #cap-target * { font-family: 'Inter','Helvetica Neue',sans-serif !important; }
#cap-target table { border-collapse: collapse !important; background: #fefdfa !important; width: 100% !important; }
#cap-target thead th, #cap-target tr:first-child th {
  background: #1f2430 !important; color: #f3efe7 !important;
  font-size: 12px !important; font-weight: 600 !important; letter-spacing: .08em !important;
  text-transform: uppercase !important; padding: 14px 16px !important; text-align: left !important;
  border: none !important;
}
#cap-target tbody td, #cap-target td {
  background: #fefdfa !important; color: #1f2430 !important;
  font-size: 14px !important; padding: 13px 16px !important;
  border: none !important; border-bottom: 1px solid #ece6da !important; vertical-align: top !important;
}
#cap-target tbody tr:nth-child(even) td { background: #f6f1e8 !important; }
#cap-target a, #cap-target .src, #cap-target [class*=src] { color: #5a6d9a !important; }
"""

# Standard text-node scrub applied to RNR tables (subject->Brand-Y, locations/themed gone).
RNR_SCRUB_JS = r"""
  const reps = [
    [/Rock\s*N\s*Roll\s*Sushi|Rock\s*N\s*Roll|\bRNR\b/gi, 'Concept X'],
    [/Birmingham[-\s]?Hoover|Birmingham|Mountain Brook|Vestavia Hills|Vestavia|Hoover|Riverchase|Huntsville|Colonnade|Cahaba[^,.]*|Summit|US-?280|Alabama|\bAL\b|\bGeorgia\b/gi, 'Trade Area'],
    [/\b[a-z0-9.-]+\.(com|net|org)\b/gi, ''],
    [/NAME-MATCH/g, ''],
    // comp name was glued to its price in source cells: "Comp D$5.95" -> "Comp D  $5.95"
    [/(Comp [A-K])\s*\$/g, '$1  $'],
  ];
"""

def frame_and_scrub(page, table_selector, drop_cols=None, comp_map=None,
                    width=1100, extra_reps_js="[]"):
    """Clone ONE table into an isolated #cap-target frame, drop columns, scrub text,
    apply comp_map (name->letter), neutral palette. Returns the post-scrub cell texts."""
    return page.evaluate(
        r"""(args) => {
          const { sel, drop, width, comp } = args;
          const src = document.querySelector(sel);
          if (!src) return ['__NO_TABLE__'];
          document.getElementById('cap-target')?.remove();
          const frame = document.createElement('div');
          frame.id = 'cap-target';
          frame.style.cssText = `position:fixed;left:0;top:0;z-index:99999;background:#fefdfa;`
            + `padding:0;width:${width}px;box-sizing:border-box;border:1px solid #e6e0d4;`;
          const tbl = src.cloneNode(true);
          frame.appendChild(tbl);
          document.body.appendChild(frame);
          // remove highest column index first so earlier removals don't re-index later ones
          (drop || []).slice().sort((a,b)=>b-a).forEach(ci => {
            tbl.querySelectorAll(`tr > *:nth-child(${ci})`).forEach(c => c.remove());
          });
          """ + RNR_SCRUB_JS + r"""
          const compEntries = Object.entries(comp || {}).sort((a,b)=>b[0].length-a[0].length);
          const walk = document.createTreeWalker(frame, NodeFilter.SHOW_TEXT);
          const texts = []; let n;
          while ((n = walk.nextNode())) {
            let v = n.nodeValue;
            for (const [name, letter] of compEntries) {
              v = v.split(name).join('Comp ' + letter);
            }
            for (const [re, to] of reps) v = v.replace(re, to);
            v = v.replace(/\s{2,}/g, ' ').replace(/\s+([,.;])/g, '$1');
            if (v !== n.nodeValue) n.nodeValue = v;
            if (n.nodeValue.trim()) texts.push(n.nodeValue.trim());
          }
          return texts;
        }""",
        {"sel": table_selector, "drop": drop_cols or [], "width": width, "comp": comp_map or {}},
    )


def capture_wages(page):
    """Brand-Y (RNR) wage benchmarks — first operations table, drop NOTES+SOURCE cols."""
    page.goto(RNR_URL, wait_until="networkidle")
    page.click('.tab-nav-tab[data-tab="operations"]')
    page.wait_for_timeout(400)
    labels = frame_and_scrub(page, '#panel-operations table', drop_cols=[6, 7], width=1080)
    page.add_style_tag(content=NEUTRAL_TABLE_CSS)
    page.wait_for_timeout(150)
    SHOTS.mkdir(parents=True, exist_ok=True)
    out = SHOTS / "module-03-wages-y.png"
    page.locator('#cap-target').screenshot(path=str(out))
    return out, labels


def capture_pricing(page):
    """Brand-Y (RNR) item-level rolls pricing table (parallels Brand-X bagel pricing)."""
    page.goto(RNR_URL, wait_until="networkidle")
    page.click('.tab-nav-tab[data-tab="pricing"]')
    page.wait_for_timeout(400)
    # first pricing table is the Classic Rolls ITEM table (ITEM|LOW COMP|HIGH COMP|MKT AVG)
    labels = frame_and_scrub(page, '#panel-pricing table', comp_map=RNR_COMP_MAP, width=980)
    page.add_style_tag(content=NEUTRAL_TABLE_CSS)
    page.wait_for_timeout(150)
    SHOTS.mkdir(parents=True, exist_ok=True)
    out = SHOTS / "module-01-pricing-y.png"
    page.locator('#cap-target').screenshot(path=str(out))
    return out, labels


def capture_sentiment_x(page):
    """Concept Y (B&Co, PRE-OPENING) sentiment — full field with the subject sorted to the
    bottom (rating 0) and shown as an orange 'no guest sentiment yet' callout bar."""
    page.goto(BCO_URL, wait_until="networkidle")
    page.evaluate("() => document.getElementById('sentimentChart')?.scrollIntoView({block:'center'})")
    page.wait_for_function("() => !!(window.Chart && Chart.getChart && Chart.getChart('sentimentChart'))")
    page.wait_for_timeout(400)
    result = page.evaluate(r"""() => {
      const ORANGE='#e85d1c', PERID='#5a6d9a';
      const chart = Chart.getChart('sentimentChart');
      const subjRe = /Bagels?\s*and\s*Co/i;
      const ds = chart.data.datasets[0];
      // keep the subject; pair labels with values and sort rating-descending so the
      // pre-opening subject (rating 0, no sentiment yet) sorts to the bottom of the field
      let rows = chart.data.labels.map((l, i) => ({ isSubj: subjRe.test(l), val: ds.data[i] }));
      // pre-opening subject pinned to the TOP; comps fade best -> worst below it
      const comps = rows.filter(r => !r.isSubj).sort((a, b) => b.val - a.val);
      const subj = rows.find(r => r.isSubj);
      rows = subj ? [subj, ...comps] : comps;
      const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
      let ci = 0;
      const newLabels = rows.map(r => r.isSubj ? 'Concept Y' : `Comp ${LETTERS[ci++]}   ${r.val}★`);
      const subjIdx = rows.findIndex(r => r.isSubj);
      chart.data.labels = newLabels;
      ds.data = rows.map(r => r.val);
      // comp bars fade lightest (best) -> darkest (worst); subject bar orange (rating 0)
      const nC = rows.length - 1;
      const ramp = (t) => {
        const LT = [196, 206, 226], DK = [60, 74, 112];
        const h = (a, b) => ('0' + Math.round(a + (b - a) * t).toString(16)).slice(-2);
        return '#' + h(LT[0], DK[0]) + h(LT[1], DK[1]) + h(LT[2], DK[2]);
      };
      let cj = 0;
      ds.backgroundColor = rows.map(r => r.isSubj ? ORANGE : ramp(nC <= 1 ? 0 : (cj++) / (nC - 1)));
      ds.borderColor = ds.backgroundColor.slice();
      ds.borderWidth = 0;
      chart.options.scales.y.ticks.crossAlign = 'far';
      chart.options.scales.y.ticks.color = rows.map(r => r.isSubj ? ORANGE : '#2a2f3a');
      chart.options.scales.y.ticks.font = (c) => ({
        family: 'monospace', size: 13, weight: (rows[c.index] && rows[c.index].isSubj) ? '700' : '500'
      });
      if (chart.options.scales.y.grid) chart.options.scales.y.grid.display = false;
      if (chart.options.scales.x && chart.options.scales.x.ticks)
        chart.options.scales.x.ticks.color = PERID;
      if (chart.options.plugins) {
        if (chart.options.plugins.legend) chart.options.plugins.legend.display = false;
        if (chart.options.plugins.title) chart.options.plugins.title.display = false;
        if (chart.options.plugins.tooltip) chart.options.plugins.tooltip.enabled = false;
      }
      // neuter the source's end-of-bar review-count plugin
      (chart.config.plugins || []).forEach(p => {
        if (p && p.id === 'sentimentLabels') {
          ['beforeDraw','afterDraw','afterDatasetsDraw','afterDatasetDraw','afterRender']
            .forEach(h => { if (p[h]) p[h] = function(){}; });
        }
      });
      chart.options.animation = false;
      chart.options.maintainAspectRatio = false;
      const wrap = chart.canvas.parentElement;
      wrap.id = 'cap-target';
      document.body.appendChild(wrap);
      wrap.style.cssText = 'position:fixed;left:0;top:0;z-index:99999;'
        + 'background:#fefdfa;padding:26px 30px 22px;width:980px;height:480px;'
        + 'box-sizing:border-box;border:1px solid #e6e0d4;';
      chart.resize(); chart.update();
      return { labels: newLabels, subjIdx };
    }""")
    page.wait_for_timeout(350)
    page.evaluate("() => { const c = Chart.getChart('sentimentChart'); c.resize(); c.update(); }")
    page.wait_for_timeout(300)
    # draw the pre-opening 'no guest sentiment yet' callout band on the subject row,
    # directly on the canvas after the final render (no chart.update() after, or it clears)
    page.evaluate(r"""(subjIdx) => {
      const chart = Chart.getChart('sentimentChart');
      const bar = chart.getDatasetMeta(0).data[subjIdx];
      if (!bar) return;
      const a = chart.chartArea, ctx = chart.ctx, cy = bar.y, h = 18;
      ctx.save();
      ctx.fillStyle = 'rgba(232,93,28,0.15)';
      if (ctx.roundRect) { ctx.beginPath(); ctx.roundRect(a.left, cy - h/2, a.right - a.left, h, 3); ctx.fill(); }
      else { ctx.fillRect(a.left, cy - h/2, a.right - a.left, h); }
      ctx.fillStyle = '#e85d1c'; ctx.fillRect(a.left, cy - h/2, 3, h);
      ctx.fillStyle = '#b23c0c'; ctx.font = 'italic 700 12px monospace';
      ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
      ctx.fillText('PRE-OPENING · NO GUEST SENTIMENT YET', a.left + 12, cy + 1);
      ctx.restore();
    }""", result["subjIdx"])
    page.wait_for_timeout(120)
    SHOTS.mkdir(parents=True, exist_ok=True)
    out = SHOTS / "module-04-sentiment-x.png"
    page.locator('#cap-target').screenshot(path=str(out))
    return out, result["labels"]


# Category "subject vs market band" charts. Subject -> orange; Mkt High/Avg/Low -> periwinkle ramp.
CATEGORY_CONFIGS = {
    "x-breakfast": dict(url=BCO_URL, chart="chart_breakfast_sandwiches", subj="Bagels and Co",
                        brand="Concept Y", out="module-05-x-breakfast.png", tab=None),
    "x-coffee":    dict(url=BCO_URL, chart="chart_coffee", subj="Bagels and Co",
                        brand="Concept Y", out="module-05-x-coffee.png", tab=None),
    "y-rolls":     dict(url=RNR_URL, chart="chart_classic", subj="Rock N Roll|RNR",
                        brand="Concept X", out="module-05-y-rolls.png", tab="pricing"),
    "y-ramen":     dict(url=RNR_URL, chart="chart_ramen", subj="Rock N Roll|RNR",
                        brand="Concept X", out="module-05-y-ramen.png", tab="pricing"),
}

def capture_category(page, key):
    cfg = CATEGORY_CONFIGS[key]
    page.goto(cfg["url"], wait_until="networkidle")
    if cfg["tab"]:
        page.click(f'.tab-nav-tab[data-tab="{cfg["tab"]}"]')
        page.wait_for_timeout(300)
    page.evaluate(f"() => document.getElementById('{cfg['chart']}')?.scrollIntoView({{block:'center'}})")
    page.wait_for_function(
        f"() => !!(window.Chart && Chart.getChart && Chart.getChart('{cfg['chart']}'))")
    page.wait_for_timeout(400)
    labels = page.evaluate(r"""(cfg) => {
      const ORANGE='#e85d1c', P_HI='#5a6d9a', P_AVG='#7d8fb8', P_LO='#b9c4dd', PERID='#5a6d9a';
      const chart = Chart.getChart(cfg.chart);
      const subjRe = new RegExp(cfg.subj, 'i');
      const band = { 'Mkt High': P_HI, 'Mkt Avg': P_AVG, 'Mkt Low': P_LO };
      chart.data.datasets.forEach(d => {
        if (subjRe.test(d.label || '')) { d.label = cfg.brand; d.backgroundColor = ORANGE; }
        else {
          const key = String(d.label||'').replace(/\s*\(.*?\)\s*/g, '').trim();  // drop "(Comp 10)"
          d.label = key;
          d.backgroundColor = band[key] || P_AVG;
        }
        d.borderWidth = 0;
      });
      // left-align item labels, palette ticks
      chart.options.scales.y.ticks.crossAlign = 'far';
      chart.options.scales.y.ticks.color = PERID;
      chart.options.scales.y.ticks.font = { family: 'monospace', size: 12 };
      if (chart.options.scales.y.grid) chart.options.scales.y.grid.display = false;
      if (chart.options.scales.x && chart.options.scales.x.ticks)
        chart.options.scales.x.ticks.color = PERID;
      if (chart.options.plugins) {
        if (chart.options.plugins.legend) {
          chart.options.plugins.legend.display = true;
          chart.options.plugins.legend.position = 'top';
        }
        if (chart.options.plugins.title) chart.options.plugins.title.display = false;
        if (chart.options.plugins.tooltip) chart.options.plugins.tooltip.enabled = false;
      }
      // neuter any inline label plugins (review-count/value drawers)
      (chart.config.plugins || []).forEach(p => {
        if (p && /label/i.test(p.id||'')) ['afterDraw','afterDatasetsDraw','afterDatasetDraw']
          .forEach(h => { if (p[h]) p[h] = function(){}; });
      });
      chart.options.animation = false;
      chart.options.maintainAspectRatio = false;
      const rows = chart.data.labels.length;
      const wrap = chart.canvas.parentElement;
      wrap.id = 'cap-target';
      document.body.appendChild(wrap);
      wrap.style.cssText = 'position:fixed;left:0;top:0;z-index:99999;background:#fefdfa;'
        + `padding:22px 26px 18px;width:760px;height:${rows*46 + 120}px;`
        + 'box-sizing:border-box;border:1px solid #e6e0d4;';
      chart.resize(); chart.update();
      return chart.data.labels.map(l => Array.isArray(l) ? l.join(' ') : String(l));
    }""", cfg)
    page.wait_for_timeout(400)
    # Reparenting the canvas + same-tick resize can draw bars before the x-scale is
    # laid out (all bars paint to full plot width). Force a reflow so the wrapper has
    # real dimensions, then settle twice with animation off so bars map to true values.
    page.evaluate(f"""() => {{ const c=Chart.getChart('{cfg['chart']}');
      c.canvas.parentElement.offsetHeight; c.resize(); c.update('none'); }}""")
    page.wait_for_timeout(500)
    page.evaluate(f"() => {{ const c=Chart.getChart('{cfg['chart']}'); c.resize(); c.update('none'); }}")
    page.wait_for_timeout(300)
    SHOTS.mkdir(parents=True, exist_ok=True)
    out = SHOTS / cfg["out"]
    page.locator('#cap-target').screenshot(path=str(out))
    return out, labels


CAPTURES = {
    "sentiment": capture_sentiment,
    "sentiment_x": capture_sentiment_x,
    "wages": capture_wages,
    "pricing": capture_pricing,
}
CAPTURES.update({k: (lambda p, key=k: capture_category(p, key)) for k in CATEGORY_CONFIGS})


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "sentiment"
    fn = CAPTURES.get(which)
    if not fn:
        print(f"unknown capture '{which}'. options: {list(CAPTURES)}")
        sys.exit(2)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(device_scale_factor=2, viewport={"width": 1400, "height": 1300})
        page = ctx.new_page()
        out, labels = fn(page)
        browser.close()

    print(f"[capture] saved {out}  ({out.stat().st_size//1024} KB)")
    print("[labels]")
    any_leak = False
    for l in labels:
        hits = scan_leaks(l)
        flag = f"  <-- LEAK: {hits}" if hits else ""
        if hits:
            any_leak = True
        print(f"   {l}{flag}")
    print("[leak-scan]", "FAIL — leaks above" if any_leak else "OK — no brand/location/themed/'(' tokens")


if __name__ == "__main__":
    main()
