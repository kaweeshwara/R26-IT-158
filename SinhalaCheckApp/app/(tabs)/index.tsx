import React, { useState } from 'react';
import { View, Text, TextInput, Button, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import axios from 'axios';

// Your computer's WiFi IP address (same one Expo showed you)
const API_URL = 'http://192.168.8.169:8000/predict';

export default function HomeScreen() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const checkText = async () => {
    if (!text.trim()) {
      setError('Please enter some text to check');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await axios.post(API_URL, {
        text: text,
        source_score: 0.6,
        temporal_score: 0.8,
      });
      setResult(response.data);
    } catch (err) {
      setError('Could not connect to server. Check WiFi and that the server is running.');
    } finally {
      setLoading(false);
    }
  };

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

      <View style={styles.button}>
        <Button
          title={loading ? 'Checking...' : 'Check Credibility'}
          onPress={checkText}
          disabled={loading}
          color="#1F3864"
        />
      </View>

      {loading && <ActivityIndicator size="large" color="#1F3864" style={{ marginTop: 20 }} />}

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {result && (
        <View style={styles.resultBox}>
          <Text style={styles.verdict}>{result.label}</Text>
          <Text style={styles.score}>Score: {result.final_score}</Text>

          <Text style={styles.sectionTitle}>Why?</Text>
          {result.lime_explanations.map((item: any, index: number) => (
            <Text key={index} style={styles.reason}>
              • {item.word} ({item.weight > 0 ? '+' : ''}{item.weight})
            </Text>
          ))}
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
  button: { marginTop: 16, borderRadius: 10, overflow: 'hidden' },
  error: { color: 'red', marginTop: 12, textAlign: 'center' },
  resultBox: { marginTop: 24, padding: 16, backgroundColor: '#f5f5f5', borderRadius: 12 },
  verdict: { fontSize: 22, fontWeight: 'bold', color: '#1F3864', textAlign: 'center' },
  score: { fontSize: 16, color: '#333', textAlign: 'center', marginBottom: 12 },
  sectionTitle: { fontSize: 16, fontWeight: '600', marginTop: 10, marginBottom: 6 },
  reason: { fontSize: 14, color: '#444', marginBottom: 4 },
});