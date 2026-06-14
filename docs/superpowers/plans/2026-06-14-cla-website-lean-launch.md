# CLA Website Lean Launch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get `cl-analysis.com` live on Cloudflare Pages by COB Wed 2026-06-18, with all three forms working end-to-end (inline success + email notification to `josh@cl-analysis.com`) and a working `/consult` booking link.

**Architecture:** Astro 5 static site + Cloudflare Pages Functions (`/functions/api/*`). Forms submit via a shared client-side `fetch` handler (JSON body → existing Functions) that shows an inline success state instead of navigating to raw JSON. Email notifications switch from the dead MailChannels integration to Resend, called from a shared `_email.ts` helper. The domain is already on Cloudflare nameservers, so the custom-domain attach is a dashboard step with no propagation wait.

**Tech Stack:** Astro 5, TypeScript (Pages Functions), Cloudflare KV, Resend email API, `@astrojs/sitemap`, Leaflet (existing). No unit-test framework exists in this repo; verification is by `npm run build`, local `wrangler pages dev`, `curl`, and live form submission.

**Inputs still required from Josh (not code):**
- Cloudflare auth (`wrangler login`) — Task 7.
- Resend API key — pasted as a Pages secret in Task 7 (already obtained per Josh).
- `josh@cl-analysis.com` is a real, deliverable mailbox (or Cloudflare Email Routing forward) — Task 7.
- Booking page URL (Google Appointment Schedule) — Task 6, replaces the `BOOKING_URL` constant.

---

## File Structure

| File | Create/Modify | Responsibility |
|---|---|---|
| `src/layouts/Base.astro` | Modify | Add the shared async-form `<script>`; add `og:image`, `twitter:image`, `apple-touch-icon` meta. |
| `src/styles/global.css` | Modify | Add `.async-success` / `.async-error` styles. |
| `src/pages/consult.astro` | Modify | Add `data-async`/`data-success` to form; replace booking placeholder with `BOOKING_URL` button. |
| `src/pages/insights.astro` | Modify | Add `data-async`/`data-success` to newsletter form. |
| `src/pages/sample.astro` | Modify | Repoint gate form to `/api/subscribe`; honest copy; `data-async`/`data-success`. |
| `functions/api/_email.ts` | Create | Shared Resend notification helper (router-ignored `_` prefix). |
| `functions/api/lead.ts` | Modify | Replace MailChannels block with `sendNotification()`; add `RESEND_API_KEY` to `Env`. |
| `functions/api/subscribe.ts` | Modify | Replace MailChannels block with `sendNotification()`; add `RESEND_API_KEY` to `Env`. |
| `astro.config.mjs` | Modify | Add `@astrojs/sitemap` integration (robots.txt already points to it). |
| `public/og.png` | Create | 1200×630 social share image. |
| `public/apple-touch-icon.png` | Create | 180×180 home-screen icon. |
| `package.json` | Modify | Add `@astrojs/sitemap` dependency (via `npm i`). |

---

## Task 1: Shared async form handler + styles

Make every form submit via `fetch` and show an inline success message, so no user ever lands on a raw-JSON page. The existing Functions already accept `application/json`, so the client just needs to POST JSON and read `{ ok: true }`.

**Files:**
- Modify: `src/layouts/Base.astro` (add `<script>` before `</body>`)
- Modify: `src/styles/global.css` (append success/error styles)

- [ ] **Step 1: Add the shared handler script to `Base.astro`**

In `src/layouts/Base.astro`, change the body from:

```astro
  <body>
    <slot />
  </body>
```

to:

```astro
  <body>
    <slot />
    <script>
      // Progressive enhancement: any <form data-async> submits via fetch (JSON)
      // and swaps itself for an inline success message — no raw-JSON page nav.
      document.querySelectorAll('form[data-async]').forEach((form) => {
        form.addEventListener('submit', async (e) => {
          e.preventDefault();
          const f = form as HTMLFormElement;
          const btn = f.querySelector('button[type=submit]') as HTMLButtonElement | null;
          const origHtml = btn ? btn.innerHTML : '';
          if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }

          const payload = Object.fromEntries(new FormData(f).entries());
          (payload as Record<string, string>).source =
            f.getAttribute('data-source') || f.id || 'web-form';

          try {
            const res = await fetch(f.action, {
              method: 'POST',
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify(payload),
            });
            const json = await res.json().catch(() => ({}));
            if (!res.ok || !json.ok) throw new Error(json.error || 'request failed');

            const done = document.createElement('div');
            done.className = 'async-success';
            done.setAttribute('role', 'status');
            done.textContent =
              f.getAttribute('data-success') || 'Thanks — got it. I’ll be in touch shortly.';
            f.replaceWith(done);
          } catch (err) {
            let errEl = f.querySelector('.async-error') as HTMLElement | null;
            if (!errEl) {
              errEl = document.createElement('div');
              errEl.className = 'async-error';
              f.appendChild(errEl);
            }
            errEl.textContent =
              'Sorry — that didn’t go through. Please email josh@cl-analysis.com directly.';
            if (btn) { btn.disabled = false; btn.innerHTML = origHtml; }
          }
        });
      });
    </script>
  </body>
```

- [ ] **Step 2: Append success/error styles to `global.css`**

Append to the end of `src/styles/global.css`:

```css
/* ---- async form result states ---- */
.async-success {
  font-family: var(--serif);
  font-style: italic;
  font-size: 1.05rem;
  line-height: 1.55;
  color: var(--periwinkle-deep);
  padding: 1.25rem 1.25rem;
  border: 1px solid var(--tan);
  background: var(--canvas-warm);
}
.async-error {
  margin-top: 0.85rem;
  font-family: var(--mono);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  color: var(--orange);
}
```

- [ ] **Step 3: Build to verify no errors**

Run: `npm run build`
Expected: `[build] Complete!`, 7 pages built, no errors.

- [ ] **Step 4: Commit**

```bash
git add src/layouts/Base.astro src/styles/global.css
git commit -m "feat: shared async form handler + inline success/error states"
```

---

## Task 2: Wire the three forms to the async handler

Add the `data-async` / `data-success` attributes. The consult and newsletter forms keep their existing `action`; the sample gate gets repointed to `/api/subscribe` (lean: reuse newsletter capture instead of building `/api/unlock-sample`).

**Files:**
- Modify: `src/pages/consult.astro`
- Modify: `src/pages/insights.astro`
- Modify: `src/pages/sample.astro`

- [ ] **Step 1: Consult form**

In `src/pages/consult.astro`, change:

```astro
        <form class="form" id="consult-form" action="/api/lead" method="POST">
```

to:

```astro
        <form class="form" id="consult-form" action="/api/lead" method="POST"
          data-async data-source="consult-form"
          data-success="Thanks — your notes are in. I’ll review them before our call and follow up by email shortly.">
```

- [ ] **Step 2: Newsletter form**

In `src/pages/insights.astro`, change:

```astro
        <form class="signup" action="/api/subscribe" method="POST">
```

to:

```astro
        <form class="signup" action="/api/subscribe" method="POST"
          data-async data-source="insights-signup"
          data-success="You’re on the list. The first issue ships Q3 2026 — watch your inbox.">
```

- [ ] **Step 3: Sample gate form (repoint + honest copy)**

In `src/pages/sample.astro`, change:

```astro
          <p>Modules 04 (Sentiment), 05 (ezCater), and 06 (Packaged Items) load below — including the live competitive comments, per-person catering breakdowns, and per-SKU retail margin opportunities.</p>
          <form action="/api/unlock-sample" method="POST" class="gate-form">
```

to:

```astro
          <p>Drop your email and I’ll send the full sample report — Modules 04 (Sentiment), 05 (ezCater), and 06 (Packaged Items), with live competitive comments, per-person catering breakdowns, and per-SKU retail margin opportunities.</p>
          <form action="/api/subscribe" method="POST" class="gate-form"
            data-async data-source="sample-unlock"
            data-success="Got it — the full sample is on its way to your inbox. I’ll follow up personally.">
```

- [ ] **Step 4: Build to verify**

Run: `npm run build`
Expected: `[build] Complete!`, no errors.

- [ ] **Step 5: Commit**

```bash
git add src/pages/consult.astro src/pages/insights.astro src/pages/sample.astro
git commit -m "feat: wire consult/newsletter/sample forms to async handler; repoint sample gate to subscribe"
```

---

## Task 3: Resend email helper + rewire Functions

Replace the dead MailChannels calls with a single shared Resend helper. Files in `functions/api/` whose names start with `_` are ignored by the Pages router, so `_email.ts` is safe to import from the route handlers.

**Files:**
- Create: `functions/api/_email.ts`
- Modify: `functions/api/lead.ts`
- Modify: `functions/api/subscribe.ts`

- [ ] **Step 1: Create the Resend helper**

Create `functions/api/_email.ts`:

```ts
// Shared notification sender — Resend API.
// Router-ignored (filename starts with "_"), imported by route handlers.

export interface EmailEnv {
  RESEND_API_KEY?: string;
  LEAD_NOTIFY_TO?: string;   // default josh@cl-analysis.com
  LEAD_NOTIFY_FROM?: string; // default "CL Analysis <notifications@cl-analysis.com>"
}

export async function sendNotification(
  env: EmailEnv,
  opts: { subject: string; html: string; text: string; replyTo?: string },
): Promise<void> {
  if (!env.RESEND_API_KEY) {
    console.error('RESEND_API_KEY not set — skipping email');
    return;
  }
  const to = env.LEAD_NOTIFY_TO ?? 'josh@cl-analysis.com';
  const from = env.LEAD_NOTIFY_FROM ?? 'CL Analysis <notifications@cl-analysis.com>';

  try {
    const resp = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        authorization: `Bearer ${env.RESEND_API_KEY}`,
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        from,
        to: [to],
        subject: opts.subject,
        html: opts.html,
        text: opts.text,
        ...(opts.replyTo ? { reply_to: opts.replyTo } : {}),
      }),
    });
    if (!resp.ok) {
      console.error('Resend send failed', resp.status, await resp.text());
    }
  } catch (e) {
    console.error('Resend send error', e);
  }
}
```

- [ ] **Step 2: Rewire `lead.ts`**

In `functions/api/lead.ts`:

(a) Add the import at the very top of the file (above the existing comment block is fine, but put it as the first `import`):

```ts
import { sendNotification } from './_email';
```

(b) Add `RESEND_API_KEY` to the `Env` interface so it reads:

```ts
interface Env {
  LEADS_KV?: KVNamespace;
  RESEND_API_KEY?: string;
  LEAD_NOTIFY_TO?: string;   // josh@cl-analysis.com (set in Cloudflare dashboard)
  LEAD_NOTIFY_FROM?: string; // CL Analysis <notifications@cl-analysis.com>
}
```

(c) Replace the entire MailChannels block — from the line `  // 2. Email via MailChannels (free for Cloudflare Workers/Pages)` down to and including the `try { ... } catch (e) { console.error('email send error', e); }` block — with:

```ts
  // 2. Email notification via Resend
  const subject = `New consult request — ${payload.brand}`;
  const html = `
    <div style="font-family: Georgia, serif; max-width: 600px;">
      <h2 style="font-style: italic; color: #5a6d9a;">New consult request</h2>
      <table style="font-size: 14px; line-height: 1.6;">
        <tr><td><strong>Name</strong></td><td>${escapeHtml(payload.name)}</td></tr>
        <tr><td><strong>Brand</strong></td><td>${escapeHtml(payload.brand)}</td></tr>
        <tr><td><strong>Email</strong></td><td><a href="mailto:${escapeHtml(payload.email)}">${escapeHtml(payload.email)}</a></td></tr>
        <tr><td><strong>Role</strong></td><td>${escapeHtml(payload.role)}</td></tr>
        <tr><td><strong>Units</strong></td><td>${escapeHtml(payload.units || '')}</td></tr>
        <tr><td valign="top"><strong>Concern</strong></td><td>${escapeHtml(payload.concern || '')}</td></tr>
        <tr><td><strong>Source</strong></td><td>${escapeHtml(payload.source || '')}</td></tr>
        <tr><td><strong>Time</strong></td><td>${escapeHtml(payload.ts)}</td></tr>
        <tr><td><strong>IP</strong></td><td>${escapeHtml(payload.ip || '')}</td></tr>
      </table>
    </div>
  `;
  const text = `New consult request from ${payload.name} (${payload.brand}). Email: ${payload.email}.`;
  await sendNotification(env, { subject, html, text, replyTo: payload.email });
```

> Note: the existing `subject` / `html` `const` declarations inside the old MailChannels block are removed by this replacement and re-declared here, so there is no duplicate-identifier error. Confirm in Step 4's build.

- [ ] **Step 3: Rewire `subscribe.ts`**

In `functions/api/subscribe.ts`:

(a) Add at the top as the first `import`:

```ts
import { sendNotification } from './_email';
```

(b) Add `RESEND_API_KEY` to its `Env` interface:

```ts
interface Env {
  SUBSCRIBERS_KV?: KVNamespace;
  RESEND_API_KEY?: string;
  LEAD_NOTIFY_TO?: string;
  LEAD_NOTIFY_FROM?: string;
}
```

(c) Replace the MailChannels block — from `  // Optional notify` down to and including the `try { ... } catch (e) { console.error('email failed', e); }` block — with:

```ts
  // Notify via Resend
  await sendNotification(env, {
    subject: `New Insights subscriber — ${email}`,
    html: `<p style="font-family: Georgia, serif;">New subscriber: <strong>${escapeHtml(email)}</strong><br/>at ${escapeHtml(new Date().toISOString())}</p>`,
    text: `${email} subscribed at ${new Date().toISOString()}`,
    replyTo: email,
  });
```

- [ ] **Step 4: Type-check / build the Functions**

Run: `npx wrangler pages functions build functions --outdir=/tmp/fn-build 2>&1 | tail -20`
Expected: completes with no TypeScript errors. (If `wrangler` prompts to install, accept.) Alternatively run `npm run build` to confirm the Astro side is unaffected.

- [ ] **Step 5: Commit**

```bash
git add functions/api/_email.ts functions/api/lead.ts functions/api/subscribe.ts
git commit -m "feat: replace dead MailChannels with shared Resend notification helper"
```

---

## Task 4: SEO / social polish — sitemap, OG image, apple-touch-icon

`robots.txt` already points at `/sitemap-index.xml`, which does not exist yet (404). Add the sitemap integration and the two missing image assets, then reference them in `Base.astro`.

**Files:**
- Modify: `astro.config.mjs`, `package.json` (via `npm i`)
- Create: `public/og.png`, `public/apple-touch-icon.png`
- Modify: `src/layouts/Base.astro`

- [ ] **Step 1: Install and register the sitemap integration**

Run: `npm i @astrojs/sitemap`

Then edit `astro.config.mjs` to:

```js
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Pure static output for Cloudflare Pages.
// /functions directory is auto-detected by Pages and runs independently.
export default defineConfig({
  site: 'https://cl-analysis.com',
  output: 'static',
  integrations: [sitemap()],
});
```

- [ ] **Step 2: Generate the apple-touch-icon from the favicon**

The favicon is `public/favicon.svg` (40×40 viewBox). Generate a 180×180 PNG:

Run:
```bash
cd ~/Projects/cla-website
sips -s format png public/favicon.svg --resampleHeightWidth 180 180 --out public/apple-touch-icon.png 2>/dev/null \
  || (qlmanage -t -s 180 -o /tmp public/favicon.svg && sips -s format png "/tmp/favicon.svg.png" --out public/apple-touch-icon.png)
```
Expected: `public/apple-touch-icon.png` exists. Verify: `sips -g pixelWidth -g pixelHeight public/apple-touch-icon.png` → 180×180.

> If `sips` cannot read the SVG, fall back: open `public/favicon.svg` in the browser via the screenshot skill / Chrome DevTools MCP at 180×180 and save as `public/apple-touch-icon.png`.

- [ ] **Step 3: Create the OG image (1200×630)**

Create a temporary `/tmp/og.html` using the brand tokens, then screenshot it at 1200×630 to `public/og.png`:

```html
<!doctype html><html><head><meta charset="utf-8"><style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;1,9..144,400&family=JetBrains+Mono:wght@500&display=swap');
  html,body{margin:0}
  .og{width:1200px;height:630px;background:#fefdfa;display:flex;flex-direction:column;
      justify-content:center;padding:90px;box-sizing:border-box;border-top:10px solid #7d8fb8}
  .kicker{font-family:'JetBrains Mono',monospace;font-size:22px;letter-spacing:.22em;
      text-transform:uppercase;color:#7a5a3d;margin-bottom:28px}
  h1{font-family:'Fraunces',serif;font-weight:400;font-size:74px;line-height:1.05;
      letter-spacing:-.02em;color:#0a0a0a;margin:0;max-width:16em}
  h1 em{font-style:italic;color:#5a6d9a}
  .foot{font-family:'JetBrains Mono',monospace;font-size:20px;color:#9a948b;margin-top:40px;
      letter-spacing:.14em}
</style></head><body>
  <div class="og">
    <div class="kicker">Competitive Landscape Analysis</div>
    <h1>Price with <em>precision.</em><br>No assumptions. No guesswork.</h1>
    <div class="foot">cl-analysis.com</div>
  </div>
</body></html>
```

Screenshot it to `public/og.png` at exactly 1200×630 using the agent-browser or Chrome DevTools MCP (set viewport 1200×630, capture the `.og` element / full viewport, no device scaling beyond 1×). Verify: `sips -g pixelWidth -g pixelHeight public/og.png` → 1200×630.

- [ ] **Step 4: Reference the images in `Base.astro`**

In `src/layouts/Base.astro`, in the `<head>`, after the existing `<link rel="icon" ...>` line add:

```astro
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
```

And after the existing `<meta property="og:url" ...>` line add:

```astro
    <meta property="og:image" content={Astro.site ? new URL('/og.png', Astro.site).href : '/og.png'} />
    <meta name="twitter:image" content={Astro.site ? new URL('/og.png', Astro.site).href : '/og.png'} />
```

- [ ] **Step 5: Build and verify the sitemap + assets exist**

Run: `npm run build && ls dist/sitemap-index.xml dist/og.png dist/apple-touch-icon.png`
Expected: all three paths listed, build completes.

- [ ] **Step 6: Commit**

```bash
git add astro.config.mjs package.json package-lock.json public/og.png public/apple-touch-icon.png src/layouts/Base.astro
git commit -m "feat: sitemap integration + OG image + apple-touch-icon + social meta"
```

---

## Task 5: `/consult` booking link

Replace the placeholder booking block with a real CTA button to the Google Appointment Schedule page. The URL is a Josh input; use a clearly-marked constant so it's a one-line swap.

**Files:**
- Modify: `src/pages/consult.astro`

- [ ] **Step 1: Add the booking URL constant**

In `src/pages/consult.astro`, in the frontmatter (between the `---` fences at the top), add after the imports:

```astro
// Google Appointment Schedule booking URL. REPLACE before launch (Task 6 confirms the real URL).
const BOOKING_URL = 'https://calendar.app.google/REPLACE_ME';
```

- [ ] **Step 2: Replace the placeholder with the booking CTA**

Change the `.cal-embed` block from:

```astro
          <div class="cal-embed">
            <div class="placeholder">
              <div class="placeholder-icon">→</div>
              <div class="placeholder-text">
                Google Calendar appointment widget mounts here.<br/>
                <span class="muted">Replace this block with your appointment booking URL once configured.</span>
              </div>
            </div>
          </div>
```

to:

```astro
          <div class="cal-embed">
            <div class="book-cta">
              <div class="book-line">Pick a 20-minute slot that works for you.</div>
              <a class="btn-primary" href={BOOKING_URL} target="_blank" rel="noopener noreferrer">
                Open the booking calendar<span class="arrow">→</span>
              </a>
              <div class="book-fine">Opens Google Calendar · Eastern Time · no card on file</div>
            </div>
          </div>
```

- [ ] **Step 3: Add styles for the booking CTA**

In the `<style>` block of `src/pages/consult.astro`, replace the four `.placeholder*` rules with:

```css
  .book-cta { text-align: center; padding: 2rem; max-width: 24em; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
  .book-line { font-family: var(--serif); font-style: italic; font-size: 1.05rem; line-height: 1.5; color: var(--ink-soft); }
  .book-fine { font-family: var(--mono); font-size: 0.62rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
```

- [ ] **Step 4: Build and verify**

Run: `npm run build`
Expected: `[build] Complete!`, no errors. Confirm the placeholder copy is gone: `grep -rn "mounts here" dist || echo "placeholder removed"`.

- [ ] **Step 5: Commit**

```bash
git add src/pages/consult.astro
git commit -m "feat: replace /consult placeholder with Google Appointment Schedule booking CTA"
```

> **Josh input:** before the final deploy (Task 7), replace `REPLACE_ME` in `BOOKING_URL` with the real Google Appointment Schedule link, rebuild, and commit.

---

## Task 6: Local end-to-end verification with `wrangler pages dev`

Verify the forms + Functions work together locally before touching production. This runs the static build and the Functions together and exercises the real code paths (KV is mocked locally; email is best-effort and will log if no key).

**Files:** none (verification only)

- [ ] **Step 1: Build**

Run: `npm run build`
Expected: 7 pages built, `dist/` populated.

- [ ] **Step 2: Serve build + functions locally**

Run (in a background terminal): `npx wrangler pages dev dist --port 8788`
Expected: serves on `http://localhost:8788`. (Accept any wrangler install prompt.)

- [ ] **Step 3: Exercise the lead endpoint**

Run:
```bash
curl -s -X POST http://localhost:8788/api/lead \
  -H 'content-type: application/json' \
  -d '{"name":"Test User","brand":"Test Brand","email":"test@example.com","role":"Franchisor"}'
```
Expected: `{"ok":true}`. (Email will log a "RESEND_API_KEY not set" warning locally — that is fine; production has the secret.)

- [ ] **Step 4: Exercise the subscribe endpoint**

Run:
```bash
curl -s -X POST http://localhost:8788/api/subscribe \
  -H 'content-type: application/json' -d '{"email":"test@example.com"}'
```
Expected: `{"ok":true}`.

- [ ] **Step 5: Verify forms in the browser**

Open `http://localhost:8788/consult`, submit the notes form, and confirm the form is replaced by the inline `.async-success` message (no JSON page). Repeat on `/insights` and `/sample`. Use the agent-browser / Chrome DevTools MCP, or do it manually.

- [ ] **Step 6: Stop the dev server.** No commit (verification only).

---

## Task 7: Cloudflare deploy + domain + secrets (Josh-driven)

First production deploy. Several steps require Josh's Cloudflare account; run them together.

**Files:** none (infra)

- [ ] **Step 1: Authenticate wrangler**

Run: `npx wrangler login`
Expected: browser auth completes; `npx wrangler whoami` shows the account.

- [ ] **Step 2: Confirm the booking URL is real**

Confirm `BOOKING_URL` in `src/pages/consult.astro` is the actual Google Appointment Schedule link (not `REPLACE_ME`). If it was just updated, run `npm run build` and `git commit -am "chore: real booking URL"`.

- [ ] **Step 3: Create the Pages project and first deploy**

Run:
```bash
npm run build
npx wrangler pages deploy dist --project-name=cla-website
```
Expected: prints a `*.pages.dev` preview URL. Open it; the site loads.

- [ ] **Step 4: Create KV namespaces**

Run:
```bash
npx wrangler kv namespace create LEADS_KV
npx wrangler kv namespace create SUBSCRIBERS_KV
```
Then in the Cloudflare dashboard → Pages → `cla-website` → Settings → Functions → KV namespace bindings, bind:
- `LEADS_KV` → the LEADS_KV namespace
- `SUBSCRIBERS_KV` → the SUBSCRIBERS_KV namespace

- [ ] **Step 4b: Confirm `josh@cl-analysis.com` receives mail**

If `josh@cl-analysis.com` is not already a deliverable mailbox, set up Cloudflare → the cl-analysis.com zone → Email → Email Routing, and add a route forwarding `josh@cl-analysis.com` → Josh's Gmail. Send a test and confirm it arrives.

- [ ] **Step 5: Confirm Resend domain + set the secret**

In Resend, confirm `cl-analysis.com` is a verified sending domain (so `notifications@cl-analysis.com` can send). Then set the API key as a Pages secret:

```bash
npx wrangler pages secret put RESEND_API_KEY --project-name=cla-website
```
Paste the existing Resend key when prompted. (Optionally also set `LEAD_NOTIFY_TO`=`josh@cl-analysis.com` and `LEAD_NOTIFY_FROM`=`CL Analysis <notifications@cl-analysis.com>` as Pages env vars; the code defaults to these anyway.)

- [ ] **Step 6: Redeploy so bindings + secret take effect**

Run: `npx wrangler pages deploy dist --project-name=cla-website`
Then on the live preview URL, submit the consult form and confirm: (a) the inline success message shows, and (b) an email lands at `josh@cl-analysis.com`.

- [ ] **Step 7: Attach the custom domain**

Cloudflare dashboard → Pages → `cla-website` → Custom domains → add `cl-analysis.com` and `www.cl-analysis.com`. Because the domain is already on Cloudflare nameservers, records are created automatically with no propagation wait.

Verify:
```bash
dig +short cl-analysis.com
curl -sS -o /dev/null -w "%{http_code}\n" https://cl-analysis.com
```
Expected: DNS resolves; HTTP `200`.

- [ ] **Step 8: Connect GitHub for auto-deploy (optional but recommended)**

Cloudflare dashboard → Pages → `cla-website` → Settings → Build & deployments → connect the GitHub repo `joshp205-maker/cla-website`, production branch `main`, build command `npm run build`, output dir `dist`. After this, every `git push` redeploys.

- [ ] **Step 9: Push the branch**

```bash
git push origin main
```

---

## Task 8: Production smoke test (live render walk)

**Files:** none (verification)

- [ ] **Step 1: Walk every page on the live domain**

Open each on `https://cl-analysis.com`: `/`, `/consult`, `/programs`, `/method`, `/sample`, `/about`, `/insights`. Confirm: pages render, the Leaflet map loads, nav/footer links work, no console errors. Use the agent-browser / Chrome DevTools MCP.

- [ ] **Step 2: Live form submission**

On `https://cl-analysis.com/consult`, submit a real test entry. Confirm the inline success message shows AND an email arrives at `josh@cl-analysis.com`. Repeat the newsletter form on `/insights`.

- [ ] **Step 3: Booking link**

On `/consult`, click "Open the booking calendar" and confirm it opens the real Google Appointment Schedule page.

- [ ] **Step 4: Social/SEO sanity**

```bash
curl -s https://cl-analysis.com/sitemap-index.xml -o /dev/null -w "sitemap: %{http_code}\n"
curl -s https://cl-analysis.com/og.png -o /dev/null -w "og: %{http_code}\n"
```
Expected: both `200`.

- [ ] **Step 5: Done.** Site is live, forms work, leads email through. Update `README.md` "Pending integrations" checklist to reflect what's now complete (optional cleanup commit).

---

## Self-Review notes

- **Spec coverage:** A (Task 7) · B (Tasks 1–2) · C (Task 3 + Task 7 secret/domain) · D (Task 5) · E (Task 4) · F (Tasks 6 + 8). All six workstreams mapped.
- **Sample gate:** spec's lean decision (reuse subscribe, no `/api/unlock-sample`) implemented in Task 2 Step 3.
- **MailChannels removal:** Task 3 replaces it in both Functions; no remaining `mailchannels` reference should exist after Task 3 (`grep -rn mailchannels functions` → empty).
- **Type consistency:** helper is `sendNotification(env, { subject, html, text, replyTo })` — same signature used in both `lead.ts` and `subscribe.ts`. `EmailEnv` fields (`RESEND_API_KEY`, `LEAD_NOTIFY_TO`, `LEAD_NOTIFY_FROM`) are a subset of each route's `Env`, which is compatible structurally.
