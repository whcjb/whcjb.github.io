/**
 * Cloudflare Worker — Azure Neural TTS 代理
 *
 * 环境变量（在 CF Dashboard > Worker > Settings > Variables 中设置）：
 *   AZURE_KEY     - Azure Speech 订阅密钥
 *   AZURE_REGION  - Azure 区域，如 eastasia / southeastasia / eastus
 *
 * 部署后将 Worker URL 填入 reading-chapter.html 的 TTS_WORKER_URL 变量。
 */

const ALLOWED_ORIGINS = [
  'https://whcjb.github.io',
  'http://localhost:4000',
  'http://127.0.0.1:4000',
];

const CORS_HEADERS = {
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const allowOrigin = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];

    // ── CORS preflight ──
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: { ...CORS_HEADERS, 'Access-Control-Allow-Origin': allowOrigin },
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method Not Allowed', { status: 405 });
    }

    // ── 解析请求体 ──
    let body;
    try {
      body = await request.json();
    } catch {
      return jsonError(400, 'invalid_json', allowOrigin);
    }

    const text  = (body.text  || '').trim().slice(0, 2000); // 最多 2000 字符/次
    const voice = (body.voice || 'zh-CN-XiaoxiaoNeural').replace(/[^a-zA-Z0-9\-]/, '');
    if (!text) return jsonError(400, 'empty_text', allowOrigin);

    // ── 构造 SSML ──
    const ssml = `<speak version='1.0' xml:lang='zh-CN'>
  <voice name='${voice}'>
    <prosody rate='0%'>${escapeXml(text)}</prosody>
  </voice>
</speak>`;

    // ── 调用 Azure TTS ──
    const azureUrl = `https://${env.AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1`;
    let azureResp;
    try {
      azureResp = await fetch(azureUrl, {
        method: 'POST',
        headers: {
          'Ocp-Apim-Subscription-Key': env.AZURE_KEY,
          'Content-Type': 'application/ssml+xml',
          'X-Microsoft-OutputFormat': 'audio-16khz-32kbitrate-mono-mp3',
          'User-Agent': 'ReadingApp/1.0',
        },
        body: ssml,
      });
    } catch (e) {
      return jsonError(502, 'upstream_error', allowOrigin);
    }

    if (!azureResp.ok) {
      const errCode = azureResp.status === 429 ? 'quota_exceeded' : 'upstream_error';
      return new Response(JSON.stringify({ error: errCode }), {
        status: azureResp.status,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': allowOrigin,
        },
      });
    }

    // ── 返回 MP3 ──
    const audio = await azureResp.arrayBuffer();
    return new Response(audio, {
      status: 200,
      headers: {
        'Content-Type': 'audio/mpeg',
        'Cache-Control': 'no-store',
        'Access-Control-Allow-Origin': allowOrigin,
      },
    });
  },
};

function escapeXml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function jsonError(status, code, origin) {
  return new Response(JSON.stringify({ error: code }), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': origin,
    },
  });
}
