import axios from 'axios';

export const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

const TOKENS_KEY = 'nominate_tokens';

export function getTokens() {
  try {
    return JSON.parse(localStorage.getItem(TOKENS_KEY)) || null;
  } catch {
    return null;
  }
}

export function setTokens(tokens) {
  if (tokens) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
  } else {
    localStorage.removeItem(TOKENS_KEY);
  }
}

const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  const tokens = getTokens();
  if (tokens?.access_token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${tokens.access_token}`;
  }
  return config;
});

let refreshPromise = null;

async function refreshAccessToken() {
  const tokens = getTokens();
  if (!tokens?.refresh_token) throw new Error('No refresh token');
  const { data } = await axios.post(
    `${BASE_URL}/auth/refresh`,
    {},
    { headers: { Authorization: `Bearer ${tokens.refresh_token}` } },
  );
  setTokens({ ...tokens, access_token: data.access_token });
  return data.access_token;
}

// 401s from these mean bad credentials, not an expired access token.
const NO_REFRESH = ['/auth/login', '/auth/signup', '/auth/google', '/auth/refresh'];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    const skipRefresh = NO_REFRESH.some((path) => config?.url?.startsWith(path));
    if (response?.status === 401 && !config._retried && !skipRefresh) {
      config._retried = true;
      try {
        refreshPromise = refreshPromise || refreshAccessToken();
        const accessToken = await refreshPromise;
        refreshPromise = null;
        config.headers.Authorization = `Bearer ${accessToken}`;
        return api(config);
      } catch {
        refreshPromise = null;
        setTokens(null);
        window.dispatchEvent(new Event('nominate:logout'));
      }
    }
    return Promise.reject(error);
  },
);

export default api;
