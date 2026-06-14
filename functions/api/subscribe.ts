import { sendNotification } from './_email';

// Cloudflare Pages Function — POST /api/subscribe
// Newsletter signup. Writes email to KV, notifies you, returns ok.

interface Env {
  SUBSCRIBERS_KV?: KVNamespace;
  RESEND_API_KEY?: string;
  LEAD_NOTIFY_TO?: string;
  LEAD_NOTIFY_FROM?: string;
}

function sanitize(s: string, max = 200): string {
  return String(s ?? '').slice(0, max).replace(/[<>]/g, '');
}
function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export const onRequestPost: PagesFunction<Env> = async ({ request, env }) => {
  let email = '';
  try {
    const ct = request.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      const j = await request.json() as { email?: string };
      email = sanitize(j.email ?? '');
    } else {
      const form = await request.formData();
      email = sanitize(String(form.get('email') ?? ''));
    }
  } catch {
    return new Response(JSON.stringify({ ok: false, error: 'invalid payload' }), { status: 400 });
  }

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return new Response(JSON.stringify({ ok: false, error: 'invalid email' }), { status: 400 });
  }

  if (env.SUBSCRIBERS_KV) {
    try {
      await env.SUBSCRIBERS_KV.put(`sub:${email}`, JSON.stringify({
        email,
        ts: new Date().toISOString(),
        ip: request.headers.get('CF-Connecting-IP'),
      }));
    } catch (e) { console.error('KV write failed', e); }
  }

  // Notify via Resend
  await sendNotification(env, {
    subject: `New Insights subscriber — ${email}`,
    html: `<p style="font-family: Georgia, serif;">New subscriber: <strong>${escapeHtml(email)}</strong><br/>at ${escapeHtml(new Date().toISOString())}</p>`,
    text: `${email} subscribed at ${new Date().toISOString()}`,
    replyTo: email,
  });

  return new Response(JSON.stringify({ ok: true }), { headers: { 'content-type': 'application/json' } });
};
