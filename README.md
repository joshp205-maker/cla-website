# cl-analysis.com

Marketing site for **Competitive Landscape Analysis** — built on Astro, deployed to Cloudflare Pages.

## Stack

| Layer | Choice |
|---|---|
| Framework | Astro 5 (static output) |
| Hosting | Cloudflare Pages |
| Adapter | `@astrojs/cloudflare` |
| Maps | Leaflet + OpenStreetMap tiles (full-color) |
| Type | Fraunces (display) · Manrope (body) · JetBrains Mono (UI labels) |
| API | Cloudflare Pages Functions in `/functions/api/*` |
| Storage | Cloudflare KV (`LEADS_KV`, `SUBSCRIBERS_KV`) |
| Email | MailChannels (free from Cloudflare workers) |

## Develop

```bash
npm install
npm run dev      # http://127.0.0.1:4321
npm run build    # writes ./dist
```

## Project layout

```
src/
  layouts/Base.astro       # html shell + font loading
  styles/tokens.css        # palette, type, spacing
  styles/global.css        # base reset + buttons + animations
  components/
    Nav.astro              # sticky nav w/ precision-crosshair logo
    Hero.astro             # h1 + HUD readout + money card
    Anthem.astro           # dark band — Real data, for real use, in real time
    TradeMap.astro         # Leaflet OSM map (reusable, configurable)
    ModuleGrid.astro       # 4-up + ezCater wide + 3PD wide + Packaged wide
    Consultant.astro       # white-label CLA section
    Trust.astro            # 3× verified · 100% cited · 14-day
    CtaBand.astro          # pre-footer dark CTA
    Footer.astro           # soft-grey footer
  pages/
    index.astro            # homepage
    consult.astro          # /consult — Google Calendar embed + pre-call notes
    programs.astro         # /programs — 4 program tiles
    method.astro           # /method — 4-step pipeline + promise card
    sample.astro           # /sample — modules 01-03 public + email gate
    about.astro            # /about — founder + brand story
    insights.astro         # /insights — bi-monthly newsletter (Q3 2026)
functions/api/
  lead.ts                  # POST → KV + MailChannels
  subscribe.ts             # POST → KV + notify
wrangler.toml              # Cloudflare Pages config (KV bindings)
```

## Deploy (first time)

```bash
# 1. Auth wrangler
npx wrangler login

# 2. Create KV namespaces, copy IDs into wrangler.toml
npx wrangler kv namespace create LEADS_KV
npx wrangler kv namespace create SUBSCRIBERS_KV

# 3. Set email secrets (one-time)
npx wrangler pages secret put LEAD_NOTIFY_TO       # → hello@cl-analysis.com
npx wrangler pages secret put LEAD_NOTIFY_FROM     # → noreply@cl-analysis.com

# 4. First deploy
npm run build
npx wrangler pages deploy dist --project-name=cla-website

# 5. Connect cl-analysis.com domain in Cloudflare dashboard → Pages → Custom domains
```

After the first push, every `git push` to the connected branch redeploys automatically (set up GitHub integration in the Cloudflare Pages project).

## Palette (locked)

| Token | Value | Use |
|---|---|---|
| `--canvas` | `#fefdfa` | Page background (50%) |
| `--periwinkle` | `#7d8fb8` | Primary brand, CTAs, italic accent (22%) |
| `--periwinkle-deep` | `#5a6d9a` | Hover state, deep accent |
| `--tan` | `#b89f7c` | Frames, dividers (10%) |
| `--cocoa` | `#7a5a3d` | Mono accent labels (5%) |
| `--ink` | `#0a0a0a` | Text, hairlines (8%) |
| `--grey` | `#9a948b` | Muted UI (3%) |
| `--orange` | `#e85d1c` | Alert / money line only (≤2%) |
| `--dark` | `#1a1814` | Dark anthem + CTA bands |

## Pending integrations

- [ ] Google Calendar appointment embed → `/consult` (replace placeholder block)
- [ ] Set up KV namespaces in Cloudflare dashboard, paste IDs into `wrangler.toml`
- [ ] Configure MailChannels domain verification for `cl-analysis.com` SPF/DKIM
- [ ] Add favicon + OG image + apple-touch-icon to `/public/`
- [ ] Connect GitHub repo to Cloudflare Pages for auto-deploy
