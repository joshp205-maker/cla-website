// Shared notification sender — Resend API.
// Router-ignored (filename starts with "_"), imported by route handlers.

export interface EmailEnv {
  RESEND_API_KEY?: string;
  LEAD_NOTIFY_TO?: string;   // default joshp205@gmail.com
  LEAD_NOTIFY_FROM?: string; // default "Josh Patrick — CLA <hello@cl-analysis.com>"
}

export async function sendNotification(
  env: EmailEnv,
  opts: { subject: string; html: string; text: string; replyTo?: string },
): Promise<void> {
  if (!env.RESEND_API_KEY) {
    console.error('RESEND_API_KEY not set — skipping email');
    return;
  }
  // Notifications go to Josh's inbox; FROM uses the Resend-verified
  // cl-analysis.com domain (matches the proven-good wizard sender).
  const to = env.LEAD_NOTIFY_TO ?? 'joshp205@gmail.com';
  const from = env.LEAD_NOTIFY_FROM ?? 'Josh Patrick — CLA <hello@cl-analysis.com>';

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
