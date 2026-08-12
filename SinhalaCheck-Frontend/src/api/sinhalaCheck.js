import { API_BASE_URL } from '../config';

const REQUEST_TIMEOUT_MS = 25000;

async function request(path, { method = 'GET', body, signal } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
  if (signal) {
    signal.addEventListener?.('abort', () => ctrl.abort());
  }

  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
  } catch (err) {
    clearTimeout(timer);
    if (err?.name === 'AbortError') {
      throw new ApiError('Request timed out. Is the backend running?', 0);
    }
    throw new ApiError(
      `Could not reach the backend at ${API_BASE_URL}.\n` +
        'On a physical device, make sure your phone and PC are on the same Wi-Fi.',
      0,
    );
  }
  clearTimeout(timer);

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!res.ok) {
    const message = extractErrorMessage(data) || `Request failed (${res.status})`;
    throw new ApiError(message, res.status, data);
  }
  return data;
}

function extractErrorMessage(data) {
  if (!data) return null;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((e) => {
        const loc = Array.isArray(e?.loc) ? e.loc.join('.') : '';
        return `${loc ? `${loc}: ` : ''}${e?.msg ?? 'Invalid input'}`;
      })
      .join('\n');
  }
  return null;
}

export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export function analyze(payload) {
  const body = {
    url: payload.url,
  };
  if (payload.text) body.text = payload.text;
  if (payload.published_date) body.published_date = payload.published_date;
  if (payload.recirculated !== undefined && payload.recirculated !== null)
    body.recirculated = payload.recirculated;
  if (payload.cross_count !== undefined && payload.cross_count !== null)
    body.cross_count = payload.cross_count;
  if (payload.seen_count !== undefined && payload.seen_count !== null)
    body.seen_count = payload.seen_count;

  return request('/analyze', { method: 'POST', body });
}

export function getHealth() {
  return request('/');
}

export function getSources() {
  return request('/sources');
}
