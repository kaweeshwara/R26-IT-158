import axios from 'axios';

export const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '');

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000,
  headers: {'Content-Type': 'application/json'},
});

export async function analyzeArticle(request) {
  const response = await client.post('/analyze', request);
  return response.data;
}

export function getApiError(error) {
  if (error.response?.data?.detail) {
    return String(error.response.data.detail);
  }
  if (error.code === 'ECONNABORTED') {
    return 'The analysis timed out. Try again or disable LIME explanations.';
  }
  if (error.request) {
    return `Cannot reach the SinhalaCheck API at ${API_BASE_URL}. Check the API address and that the services are running.`;
  }
  return error.message || 'The analysis request failed.';
}
