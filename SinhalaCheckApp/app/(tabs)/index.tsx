import React, { useState } from 'react';
import { View, Text, TextInput, Button, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const SPACE_URL = 'https://wishmitharuwanpathirana-sinhalacheck-api.hf.space';
const HISTORY_KEY = 'sinhalacheck_history';
const SHOW_LIME = true;

const fetchWithTimeout = async (url: string, options: any = {}, timeout = 90000) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(id);
    return response;
  } catch (err) {
    clearTimeout(id);
    throw err;
  }
};

const calculateYearsOld = (dateStr: string): number | null => {
  if (!dateStr) return null;
  const inputDate = new Date(dateStr);
  if (isNaN(inputDate.getTime())) return null;
  const now = new Date();
  const years = (now.getTime() - inputDate.getTime()) / (1000 * 60 * 60 * 24 * 365);
  return Math.round(years * 10) / 10;
};

export default function HomeScreen() {
  const [text, setText] = useState('');
  const [publishDate, setPublishDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const saveToHistory = async (checkedText: string, response: any) => {
    try {
      const existing = await AsyncStorage.getItem(HISTORY_KEY);
      const history = existing ? JSON.parse(existing) : [];
      const newEntry = {
        id: Date.now().toString(),
        text: checkedText,
        label: response.label,
        score: response.final_score,
        date: new Date().toLocaleString(),
      };
      const updated = [newEntry, ...history].slice(0, 20);
      await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
    } catch (e) {
      console.log('Failed to save history', e);
    }
  };

  const checkText = async () => {
    if (!text.trim()) {
      setError('Please enter some text to check');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const submitRes = await fetchWithTimeout(`${SPACE_URL}/gradio_api/call/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: [text, 0.6, 0.8] }),
      });

      if (!submitRes.ok) {
        setError('Server error. Please try again in a moment.');
        return;
      }

      const submitData = await submitRes.json();
      const eventId = submitData.event_id;

      const resultRes = await fetchWithTimeout(`${SPACE_URL}/gradio_api/call/predict/${eventId}`);
      const resultText = await resultRes.text();
      const dataLine = resultText.split('\n').find((line) => line.startsWith('data:'));

      if (!dataLine) {
        setError('Unexpected response from server. Please try again.');
        return;
      }

      const parsed = JSON.parse(dataLine.replace('data:', '').trim());
      const finalResult = parsed[0];

      setResult(finalResult);
      await saveToHistory(text, finalResult);
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setError('Request timed out — the server might be busy, please try again.');
      } else if (err.message?.includes('Network request failed')) {
        setError('No internet connection. Please check your WiFi or mobile data.');
      } else {
        setError('Something went wrong. Please try again in a moment.');
      }
    } finally {
      setLoading(false);
    }
  };

  const yearsOld = calculateYearsOld(publishDate);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>SinhalaCheck</Text>
      <Text style={styles.subtitle}>Sinhala Fake News Detector</Text>

      <TextInput
        style={styles.input}
        placeholder="Paste Sinhala news text here..."
        placeholderTextColor="#999"
        multiline
        numberOfLines={6}
        value={text}
        onChangeText={setText}
      />

      <TextInput
        style={styles.dateInput}
        placeholder="Publish date (optional, e.g. 2020-04-01)"
        placeholderTextColor="#999"
        value={publishDate}
        onChangeText={setPublishDate}
      />

      <View style={styles.button}>
        <Button
          title={loading ? 'Checking...' : 'Check Credibility'}
          onPress={checkText}
          disabled={loading}
          color="#1F3864"
        />
      </View>

      {loading && <ActivityIndicator size="large" color="#1F3864" style={{ marginTop: 20 }} />}
      {loading && <Text style={styles.loadingText}>This can take 15-30 seconds...</Text>}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {result && (
        <View style={styles.resultBox}>
          <Text style={styles.verdict}>{result.label}</Text>
          <Text style={styles.score}>Score: {result.final_score}</Text>

          {yearsOld !== null && yearsOld > 1 && (
            <View style={styles.warningBox}>
              <Text style={styles.warningText}>
                🕒 {yearsOld} years old — originally published {publishDate}
              </Text>
            </View>
          )}

          {SHOW_LIME && result.lime_explanations && (
            <>
              <Text style={styles.sectionTitle}>Why?</Text>
              {result.lime_explanations.map((item: any, index: number) => (
                <Text key={index} style={styles.reason}>
                  • {item.word} ({item.weight > 0 ? '+' : ''}{item.weight})
                </Text>
              ))}
            </>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { padding: 20, paddingTop: 60 },
  title: { fontSize: 28, fontWeight: 'bold', color: '#1F3864', textAlign: 'center' },
  subtitle: { fontSize: 14, color: '#666', textAlign: 'center', marginBottom: 20 },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 10, padding: 12, fontSize: 16, textAlignVertical: 'top', minHeight: 120 },
  dateInput: { borderWidth: 1, borderColor: '#ccc', borderRadius: 10, padding: 10, fontSize: 14, marginTop: 10 },
  button: { marginTop: 16, borderRadius: 10, overflow: 'hidden' },
  loadingText: { textAlign: 'center', color: '#666', marginTop: 8, fontSize: 12 },
  error: { color: 'red', marginTop: 12, textAlign: 'center' },
  resultBox: { marginTop: 24, padding: 16, backgroundColor: '#f5f5f5', borderRadius: 12 },
  verdict: { fontSize: 22, fontWeight: 'bold', color: '#1F3864', textAlign: 'center' },
  score: { fontSize: 16, color: '#333', textAlign: 'center', marginBottom: 12 },
  warningBox: { marginTop: 10, padding: 10, borderRadius: 8, backgroundColor: '#FDF3E7', borderWidth: 1, borderColor: '#F0C878' },
  warningText: { color: '#8A5A00', fontSize: 13, fontWeight: '600', textAlign: 'center' },
  sectionTitle: { fontSize: 16, fontWeight: '600', marginTop: 10, marginBottom: 6 },
  reason: { fontSize: 14, color: '#444', marginBottom: 4 },
});