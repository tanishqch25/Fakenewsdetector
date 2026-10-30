const API_BASE = '/api';

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new Error(
      'Could not reach the analysis backend. Make sure the FastAPI server is running on port 8000.'
    );
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    /* non-JSON body */
  }

  if (!response.ok) {
    const detail = data && data.detail ? data.detail : `Request failed (HTTP ${response.status}).`;
    throw new Error(detail);
  }

  return data;
}

export function analyzeText(text) {
  return request('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
}

export function analyzeUrl(url) {
  return request('/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
}

export function checkHealth() {
  return request('/health');
}
