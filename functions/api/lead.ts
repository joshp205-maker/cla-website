// Cloudflare Pages Function — POST /api/lead
// Handles consult-form submissions: writes to KV, sends email via MailChannels,
// returns success/error to client.

interface Env {
  LEADS_KV?: KVNamespace;
  LEAD_NOTIFY_TO?: string;   // hello@cl-analysis.com (set in Cloudflare dashboard)
  LEAD_NOTIFY_FROM?: string; // noreply@cl-analysis.com
}

interface LeadPayload {
  name: string;
  brand: string;
  email: string;
  role: string;
  units?: string;
  concern?: string;
  source?: string;
  ts: string;
  ua?: string;
  ip?: string;
}

function sanitize(s: string, max = 600): string {
  return String(s ?? '').slice(0, max).replace(/[<>]/g, '');
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export const onRequestPost: PagesFunction<Env> = async (ctx) => {
  const { request, env } = ctx;
  let payload: LeadPayload;

  try {
    const ct = request.headers.get('content-type') || '';
    let data: Record<string, unknown> = {};

    if (ct.includes('application/json')) {
      data = await request.json();
    } else if (ct.includes('application/x-www-form-urlencoded') || ct.includes('multipart/form-data')) {
      const form = await request.formData();
      form.forEach((v, k) => { data[k] = v; });
    } else {
      return new Response(JSON.stringify({ ok: false, error: 'unsupported content-type' }), {
        status: 415, headers: { 'content-type': 'application/json' },
      });
    }

    payload = {
      name: sanitize(String(data.name ?? '')),
      brand: sanitize(String(data.brand ?? '')),
      email: sanitize(String(data.email ?? ''), 200),
      role: sanitize(String(data.role ?? '')),
      units: sanitize(String(data.units ?? '')),
      concern: sanitize(String(data.concern ?? ''), 2000),
      source: sanitize(String(data.source ?? 'consult-form'), 80),
      ts: new Date().toISOString(),
      ua: sanitize(request.headers.get('user-agent') ?? '', 300),
      ip: request.headers.get('CF-Connecting-IP') ?? undefined,
    };

    if (!payload.email || !payload.name || !payload.brand) {
      return new Response(JSON.stringify({ ok: false, error: 'missing required fields' }), {
        status: 400, headers: { 'content-type': 'application/json' },
      });
    }
  } catch (err) {
    return new Response(JSON.stringify({ ok: false, error: 'invalid payload' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }

  // 1. Write to KV (if bound) — best-effort
  if (env.LEADS_KV) {
    const key = `lead:${payload.ts}:${payload.email}`;
    try {
      await env.LEADS_KV.put(key, JSON.stringify(payload), {
        expirationTtl: 60 * 60 * 24 * 365, // 1yr
      });
    } catch (e) {
      // log only — don't fail the user
      console.error('KV write failed', e);
    }
  }

  // 2. Email via MailChannels (free for Cloudflare Workers/Pages)
  const to = env.LEAD_NOTIFY_TO ?? 'hello@cl-analysis.com';
  const from = env.LEAD_NOTIFY_FROM ?? 'noreply@cl-analysis.com';

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

  try {
    const resp = await fetch('https://api.mailchannels.net/tx/v1/send', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        personalizations: [{ to: [{ email: to }] }],
        from: { email: from, name: 'CL Analysis · Lead Form' },
        subject,
        content: [
          { type: 'text/html', value: html },
          { type: 'text/plain', value: `New consult request from ${payload.name} (${payload.brand}). Email: ${payload.email}.` },
        ],
        reply_to: { email: payload.email, name: payload.name },
      }),
    });

    if (!resp.ok) {
      const t = await resp.text();
      console.error('MailChannels failed', resp.status, t);
      // Still return success to user — we have the KV record
    }
  } catch (e) {
    console.error('email send error', e);
  }

  return new Response(JSON.stringify({ ok: true }), {
    status: 200, headers: { 'content-type': 'application/json' },
  });
};
