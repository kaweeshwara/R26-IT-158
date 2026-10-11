import AsyncStorage from '@react-native-async-storage/async-storage';

const HISTORY_KEY = '@sinhalacheck/history/v1';
const STUDY_KEY = '@sinhalacheck/study-responses/v1';

async function readList(key) {
  const raw = await AsyncStorage.getItem(key);
  if (raw === null) return [];
  const value = JSON.parse(raw);
  if (!Array.isArray(value)) {
    throw new Error(`Stored data for ${key} is invalid.`);
  }
  return value;
}

export async function getHistory() {
  return readList(HISTORY_KEY);
}

export async function saveHistoryRecord(record) {
  const current = await getHistory();
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify([record, ...current].slice(0, 100)));
}

export async function clearHistory() {
  await AsyncStorage.removeItem(HISTORY_KEY);
}

export async function getStudyResponses() {
  return readList(STUDY_KEY);
}

export async function saveStudyResponse(response) {
  const current = await getStudyResponses();
  const duplicate = current.some(row =>
    row.participant_id === response.participant_id &&
    row.item_id === response.item_id
  );
  if (duplicate) {
    throw new Error('This participant already has a saved response for that item.');
  }
  await AsyncStorage.setItem(STUDY_KEY, JSON.stringify([...current, response]));
}

export async function clearStudyResponses() {
  await AsyncStorage.removeItem(STUDY_KEY);
}
