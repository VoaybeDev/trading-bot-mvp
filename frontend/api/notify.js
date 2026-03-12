/**
 * frontend/api/notify.js
 * Relay Telegram — reçoit les notifications de HF Spaces
 * et les transmet à l'API Telegram (HF bloque les appels directs).
 *
 * Variables d'environnement Vercel requises :
 *   TELEGRAM_TOKEN    — Token du bot Telegram
 *   TELEGRAM_CHAT_ID  — ID du chat destinataire
 *   NOTIFY_SECRET     — Clé partagée avec HF Spaces pour sécuriser le relay
 */
export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const secret = process.env.NOTIFY_SECRET || "";
  if (secret && req.headers["x-notify-secret"] !== secret) {
    return res.status(403).json({ error: "Forbidden" });
  }

  const { text } = req.body;
  if (!text) {
    return res.status(400).json({ error: "Missing 'text' field" });
  }

  const token  = process.env.TELEGRAM_TOKEN   || "";
  const chatId = process.env.TELEGRAM_CHAT_ID || "";

  if (!token || !chatId) {
    return res.status(500).json({ error: "Telegram not configured on relay" });
  }

  try {
    const response = await fetch(
      `https://api.telegram.org/bot${token}/sendMessage`,
      {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
          chat_id:    chatId,
          text:       text,
          parse_mode: "HTML",
        }),
      }
    );

    const data = await response.json();

    if (!data.ok) {
      console.error("Telegram API error:", data);
      return res.status(502).json({ error: "Telegram API error", detail: data });
    }

    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("Relay error:", err);
    return res.status(500).json({ error: "Internal relay error", detail: err.message });
  }
}