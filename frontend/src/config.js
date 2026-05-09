import Constants from 'expo-constants';
import { Platform } from 'react-native';

const PORT = 8000;

function deriveDevHost() {
  const candidates = [
    Constants?.expoConfig?.hostUri,
    Constants?.expoGoConfig?.hostUri,
    Constants?.manifest2?.extra?.expoGo?.debuggerHost,
    Constants?.manifest?.debuggerHost,
    Constants?.manifest?.hostUri,
  ];

  for (const c of candidates) {
    if (typeof c === 'string' && c.length > 0) {
      const host = c.split(':')[0];
      if (host && host !== 'localhost' && host !== '127.0.0.1') {
        return host;
      }
    }
  }

  if (Platform.OS === 'android') return '10.0.2.2';
  return 'localhost';
}

export const API_BASE_URL = `http://${deriveDevHost()}:${PORT}`;
