const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(status, payload) {
    const error = payload?.error || {};
    super(error.message || `Request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.code = error.code || 'request_failed';
    this.details = error.details;
  }
}

export async function apiRequest(path, { token, method = 'GET', body, signal } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError(0, { error: { message: 'The API is unreachable. Start the backend and try again.', code: 'network_error' } });
  }

  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { error: { message: text, code: 'invalid_response' } };
    }
  }
  if (!response.ok) throw new ApiError(response.status, payload);
  return payload;
}

export { API_BASE_URL };
