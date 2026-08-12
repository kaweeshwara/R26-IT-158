import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = '@sinhalacheck/check_history';
const MAX_ITEMS = 50;

/**
 * Persist a successful analysis so it can be reviewed later.
 * Newest items come first. Caps at MAX_ITEMS.
 */
export async function addHistoryEntry({ url, text, result }) {
  const entry = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    checkedAt: new Date().toISOString(),
    url: url || '',
    textPreview: truncate(text, 120),
    result,
  };

  const existing = await loadHistory();
  const next = [entry, ...existing].slice(0, MAX_ITEMS);
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

export async function loadHistory() {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function removeHistoryEntry(id) {
  const existing = await loadHistory();
  const next = existing.filter((item) => item.id !== id);
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

export async function clearHistory() {
  await AsyncStorage.removeItem(STORAGE_KEY);
  return [];
}

function truncate(value, max) {
  if (!value || typeof value !== 'string') return '';
  const trimmed = value.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max - 1)}…`;
}
