# CLA Website — Lean Launch Design

**Date:** 2026-06-14
**Goal:** Get `cl-analysis.com` live and fully functional by COB Wednesday, 2026-06-18.
**Scope decision:** Lean launch on **Cloudflare Pages**, real domain, working forms + email, booking via link (not embed).

---

## Current state (verified 2026-06-14)

The Astro static site is ~90% built; the *launch* is ~0% done.

**Done & good:**
- Astro 5 static site, 7 pages (`index, consult, programs, method, sample, about, insights`). Builds clean in ~6.4s (`npm run build`).
- Locked palette/fonts/components; Leaflet OSM map; two Pages Functions written (`functions/api/lead.ts`, `functions/api/subscribe.ts`).
- Domain `cl-analysis.com` is **already on Cloudflare nameservers** (`bradley`/`chelsea.ns.cloudflare.com`) — no nameserver change or propagation wait needed to attach it.

**Blocking launch (evidence):**
1. Not deployed anywhere. `dig cl-analysis.com` empty; `curl` → could-not-resolve; `wrangler whoami` → not authenticated. No A/CNAME record yet.
2. Forms show raw JSON. All 3 forms use native HTML POST with no JS; functions return `{ok:true}` JSON, so a submitter lands on a blank JSON page. No thank-you page or inline success.
3. Sample form is broken — `sample.astro` posts to `/api/unlock-sample`, which does not exist (only `lead.ts` + `subscribe.ts` exist).
4. Email won't send. `lead.ts` uses MailChannels, whose free Cloudflare integration was discontinued in 2024. Leads would land silently in KV with no notification.
5. `/consult` booking is still a placeholder block.
6. Infra unconfigured: KV namespaces not created, email secrets not set, no OG image / apple-touch-icon.

---

## Target architecture

| Layer | Choice |
|---|---|
| Hosting | Cloudflare Pages (static `dist/` + `/functions` auto-detected) |
| Domain | `cl-analysis.com` (+ `www`), already on CF NS → custom-domain attach in Pages |
| Forms | JS `fetch` → existing Pages Functions → inline success state (no page nav) |
| Lead/email | **Resend** API from within the Pages Functions (replaces dead MailChannels) |
| Lead storage | Cloudflare KV (`LEADS_KV`, `SUBSCRIBERS_KV`) — best-effort, already coded |
| Booking | Link/button on `/consult` to an external booking page (Google Appointment Schedule, default) |
| Deploy | `wrangler pages deploy` for first push; GitHub auto-deploy thereafter |

---

## Workstreams

### A. Hosting & domain
- Authenticate wrangler / Cloudflare (Josh).
- Create Pages project `cla-website`; connect GitHub repo for push-to-deploy.
- Create KV namespaces `LEADS_KV`, `SUBSCRIBERS_KV`; bind in Pages project settings.
- Attach `cl-analysis.com` + `www` as custom domains (no NS change required).

### B. Forms work end-to-end
- Add a small shared client script: intercept submit, `fetch` POST as JSON, show inline success/error, disable double-submit. Applies to consult, newsletter, and sample forms.
- **Sample gate (lean):** repoint `sample.astro`'s form from the non-existent `/api/unlock-sample` to the existing `subscribe` flow (email unlock = newsletter capture). Do **not** build a separate endpoint for launch.
- Remove/avoid any path where a user sees raw JSON.

### C. Email notifications (Resend)
- Replace the MailChannels `fetch` in `lead.ts` and `subscribe.ts` with a Resend API call.
- **Destination:** `josh@cl-analysis.com`.
- Because the destination is a domain address (not the Resend account owner's), the `onboarding@resend.dev` no-DNS path will not deliver. So: **verify `cl-analysis.com` in Resend** (add its DNS records — fast, the domain is already on Cloudflare) and send from a branded address, e.g. `notifications@cl-analysis.com`.
- **Inbox must exist:** if `josh@cl-analysis.com` is not yet a real mailbox, set up **Cloudflare Email Routing** (free) to forward it to Josh's Gmail. Confirm a test email arrives before launch.
- Store `RESEND_API_KEY` as a Pages secret. Keep KV write as the durable record; email is best-effort (never fail the user submit).

### D. `/consult` booking (lean)
- Replace the placeholder block with a styled CTA button linking to the booking URL.
- **Input required from Josh:** the booking page URL (default plan: Google Appointment Schedule via Workspace; Calendly is the fallback).

### E. SEO / social polish
- Add OG image + `apple-touch-icon`, per-page `<title>` + meta description, and verify `robots.txt` + a sitemap.

### F. Pre-launch QA + deploy
- Deploy to a Pages **preview** URL first.
- Submit each form live; confirm the notification email lands in Josh's inbox; confirm KV records written.
- Walk all 7 pages (links, map, responsive, no console errors).
- Promote to `cl-analysis.com`; re-verify the live domain serves and forms work in production.

---

## Inputs required from Josh (all small)
1. Cloudflare auth (`wrangler login` or dashboard access).
2. Resend account + `RESEND_API_KEY` (and run the domain-verify step for `cl-analysis.com`).
3. Booking page URL for `/consult` (default: Google Appointment Schedule).
4. Lead notifications go to **`josh@cl-analysis.com`** — confirm that mailbox exists or set up Cloudflare Email Routing to forward it to Gmail.

## Out of scope for Wednesday (fast-follow candidates)
- Embedded calendar booking widget on `/consult` (using a link instead).
- Dedicated `/api/unlock-sample` endpoint + gated sample-asset delivery (reusing newsletter capture instead).
- Resend domain verification for a branded `from:` address.
- `/insights` newsletter content (page exists; content is Q3 2026).

## Success criteria
- `https://cl-analysis.com` serves the site over HTTPS.
- All 3 forms submit without showing raw JSON and show an inline success message.
- A real form submission produces an email at `josh@cl-analysis.com` **and** a KV record.
- `/consult` booking button opens a working booking page.
- All 7 pages render correctly with no console errors.
