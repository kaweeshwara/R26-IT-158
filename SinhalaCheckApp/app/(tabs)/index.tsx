import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const SPACE_URL = 'https://wishmitharuwanpathirana-sinhalacheck-api.hf.space';
const HISTORY_KEY = 'sinhalacheck_history';
const SHOW_LIME = true;

// ---- Palette ----
const INK = '#1B2340';
const INDIGO = '#2A3B8F';
const INDIGO_DARK = '#1E2C6E';
const PAPER = '#F7F5F0';
const CARD = '#FFFFFF';
const BORDER = '#E4E1D8';
const MUTED = '#8B8878';
const GOLD = '#C9A227';
const EMERALD = '#1F7A5C';
const EMERALD_BG = '#E7F3EE';
const AMBER = '#A6720B';
const AMBER_BG = '#FBF1DD';
const BRICK = '#B23A3A';
const BRICK_BG = '#FBEBEB';

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

const extractTextFromHtml = (html: string): string => {
  let cleaned = html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, ' ')
    .trim();
  return cleaned.slice(0, 3000);
};

const isValidUrl = (str: string): boolean => {
  try {
    const u = new URL(str);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
};

// ---- Verdict styling lookup ----
const verdictStyle = (label: string) => {
  if (label === 'CREDIBLE') return { fg: EMERALD, bg: EMERALD_BG, ring: EMERALD };
  if (label === 'UNCERTAIN') return { fg: AMBER, bg: AMBER_BG, ring: AMBER };
  return { fg: BRICK, bg: BRICK_BG, ring: BRICK };
};

export default function HomeScreen() {
  const [text, setText] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [publishDate, setPublishDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState('');
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
    const hasUrl = urlInput.trim().length > 0;
    const hasText = text.trim().length > 0;

    if (!hasUrl && !hasText) {
      setError('Please enter some text or a URL to check');
      return;
    }
    if (hasUrl && !isValidUrl(urlInput.trim())) {
      setError('Please enter a valid URL (starting with http:// or https://)');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      let textToAnalyze = text.trim();

      if (hasUrl) {
        setLoadingStage('Fetching article from URL…');
        const pageRes = await fetchWithTimeout(urlInput.trim(), {}, 20000);
        if (!pageRes.ok) {
          setError('Could not fetch that URL. Please check the link and try again.');
          setLoading(false);
          return;
        }
        const html = await pageRes.text();
        textToAnalyze = extractTextFromHtml(html);

        if (textToAnalyze.length < 30) {
          setError('Could not extract readable text from that page.');
          setLoading(false);
          return;
        }
      }

      setLoadingStage('Analyzing credibility…');

      const submitRes = await fetchWithTimeout(`${SPACE_URL}/gradio_api/call/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: [textToAnalyze, 0.6, 0.8] }),
      });

      if (!submitRes.ok) {
        setError('Server error. Please try again in a moment.');
        return;
      }

      const submitData = await submitRes.json();
      const eventId = submitData.event_id;

      const resultRes = await fetchWithTimeout(`${SPACE_URL}/gradio_api/call/predict/${eventId}`);
      const resultText = await resultRes.text();

      const dataLines = resultText.split('\n').filter((line) => line.startsWith('data:'));
      if (dataLines.length === 0) {
        setError('Unexpected response from server. Please try again.');
        return;
      }

      const lastDataLine = dataLines[dataLines.length - 1];
      const parsed = JSON.parse(lastDataLine.replace('data:', '').trim());
      const finalResult = parsed[0];

      setResult({ ...finalResult, _analyzedText: textToAnalyze });
      await saveToHistory(textToAnalyze, finalResult);
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
      setLoadingStage('');
    }
  };

  const yearsOld = calculateYearsOld(publishDate);
  const vStyle = result ? verdictStyle(result.label) : null;
  const scorePct = result ? Math.round(result.final_score * 100) : 0;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* ---- Header with seal mark ---- */}
      <View style={styles.header}>
        <View style={styles.sealMark}>
          <View style={styles.sealCheck} />
        </View>
        <Text style={styles.title}>SinhalaCheck</Text>
        <Text style={styles.subtitle}>SINHALA MISINFORMATION VERIFIER</Text>
      </View>

      {/* ---- Input card ---- */}
      <View style={styles.card}>
        <Text style={styles.label}>NEWS TEXT</Text>
        <TextInput
          style={styles.input}
          placeholder="Paste Sinhala news text here…"
          placeholderTextColor="#B7B4A6"
          multiline
          numberOfLines={6}
          value={text}
          onChangeText={setText}
        />

        <View style={styles.dividerRow}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>OR PASTE A LINK</Text>
          <View style={styles.dividerLine} />
        </View>

        <TextInput
          style={styles.inputSmall}
          placeholder="https://example.com/article"
          placeholderTextColor="#B7B4A6"
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          value={urlInput}
          onChangeText={setUrlInput}
        />

        <Text style={[styles.label, { marginTop: 14 }]}>PUBLISH DATE <Text style={styles.labelOptional}>(optional)</Text></Text>
        <TextInput
          style={styles.inputSmall}
          placeholder="e.g. 2020-04-01"
          placeholderTextColor="#B7B4A6"
          value={publishDate}
          onChangeText={setPublishDate}
        />

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={checkText}
          disabled={loading}
          activeOpacity={0.85}
        >
          {loading ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.buttonText}>CHECK CREDIBILITY</Text>
          )}
        </TouchableOpacity>

        {loading && <Text style={styles.loadingText}>{loadingStage || 'This can take 15–30 seconds…'}</Text>}
        {error ? <Text style={styles.error}>{error}</Text> : null}
      </View>

      {/* ---- Result "certificate" card ---- */}
      {result && vStyle && (
        <View style={styles.resultCard}>
          <View style={styles.resultTopRow}>
            <Text style={styles.resultEyebrow}>VERDICT</Text>
            <View style={[styles.scoreBadge, { borderColor: vStyle.ring }]}>
              <Text style={[styles.scoreBadgeText, { color: vStyle.fg }]}>{scorePct}</Text>
            </View>
          </View>

          <Text style={[styles.verdict, { color: vStyle.fg }]}>{result.label}</Text>
          <View style={[styles.verdictPill, { backgroundColor: vStyle.bg }]}>
            <Text style={[styles.verdictPillText, { color: vStyle.fg }]}>Fusion score {result.final_score}</Text>
          </View>

          {result._analyzedText && (
            <View style={styles.quoteBox}>
              <Text style={styles.quoteMark}>“</Text>
              <Text style={styles.quoteText} numberOfLines={4}>{result._analyzedText}</Text>
            </View>
          )}

          {yearsOld !== null && yearsOld > 1 && (
            <View style={styles.warningBanner}>
              <Text style={styles.warningText}>
                ⏱ {yearsOld} years old — originally published {publishDate}
              </Text>
            </View>
          )}

          {SHOW_LIME && result.lime_explanations && (
            <View style={styles.limeSection}>
              <View style={styles.dividerRow}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>WHY THIS VERDICT</Text>
                <View style={styles.dividerLine} />
              </View>
              {result.lime_explanations.map((item: any, index: number) => (
                <View key={index} style={styles.reasonRow}>
                  <View
                    style={[
                      styles.reasonDot,
                      { backgroundColor: item.weight > 0 ? BRICK : EMERALD },
                    ]}
                  />
                  <Text style={styles.reasonWord}>{item.word}</Text>
                  <Text style={styles.reasonWeight}>
                    {item.weight > 0 ? '+' : ''}{item.weight}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: PAPER },
  content: { padding: 20, paddingTop: 56, paddingBottom: 60 },

  header: { alignItems: 'center', marginBottom: 28 },
  sealMark: {
    width: 52, height: 52, borderRadius: 26,
    backgroundColor: INDIGO, alignItems: 'center', justifyContent: 'center',
    marginBottom: 12, borderWidth: 2, borderColor: GOLD,
  },
  sealCheck: {
    width: 18, height: 10,
    borderLeftWidth: 3, borderBottomWidth: 3, borderColor: '#fff',
    transform: [{ rotate: '-45deg' }], marginTop: -2,
  },
  title: { fontSize: 26, fontWeight: '800', color: INK, letterSpacing: 0.2 },
  subtitle: { fontSize: 11, fontWeight: '600', color: MUTED, letterSpacing: 1.4, marginTop: 4 },

  card: {
    backgroundColor: CARD, borderRadius: 18, padding: 18,
    borderWidth: 1, borderColor: BORDER,
    shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 10, shadowOffset: { width: 0, height: 4 },
    elevation: 1,
  },
  label: { fontSize: 11, fontWeight: '700', color: MUTED, letterSpacing: 1, marginBottom: 8 },
  labelOptional: { fontWeight: '400', color: '#C4C1B4', letterSpacing: 0 },
  input: {
    borderWidth: 1, borderColor: BORDER, borderRadius: 12, padding: 12,
    fontSize: 15, color: INK, textAlignVertical: 'top', minHeight: 120, backgroundColor: '#FCFBF9',
  },
  inputSmall: {
    borderWidth: 1, borderColor: BORDER, borderRadius: 12, padding: 11,
    fontSize: 14, color: INK, backgroundColor: '#FCFBF9',
  },

  dividerRow: { flexDirection: 'row', alignItems: 'center', marginVertical: 16 },
  dividerLine: { flex: 1, height: 1, backgroundColor: BORDER },
  dividerText: { fontSize: 10, fontWeight: '700', color: MUTED, letterSpacing: 1, marginHorizontal: 10 },

  button: {
    backgroundColor: INDIGO, borderRadius: 14, paddingVertical: 15,
    alignItems: 'center', marginTop: 18,
    shadowColor: INDIGO_DARK, shadowOpacity: 0.25, shadowRadius: 8, shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  buttonDisabled: { backgroundColor: '#9AA3C8' },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 13, letterSpacing: 1 },

  loadingText: { textAlign: 'center', color: MUTED, marginTop: 10, fontSize: 12 },
  error: { color: BRICK, marginTop: 12, textAlign: 'center', fontSize: 13 },

  resultCard: {
    backgroundColor: CARD, borderRadius: 18, padding: 20, marginTop: 20,
    borderWidth: 1.5, borderColor: BORDER, borderStyle: 'dashed',
  },
  resultTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  resultEyebrow: { fontSize: 11, fontWeight: '700', color: MUTED, letterSpacing: 1.4 },
  scoreBadge: {
    width: 44, height: 44, borderRadius: 22, borderWidth: 2,
    alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff',
  },
  scoreBadgeText: { fontWeight: '800', fontSize: 14 },

  verdict: { fontSize: 28, fontWeight: '800', marginTop: 10, letterSpacing: 0.3 },
  verdictPill: {
    alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 5,
    borderRadius: 20, marginTop: 8,
  },
  verdictPillText: { fontSize: 12, fontWeight: '700' },

  quoteBox: { marginTop: 18, paddingLeft: 14, borderLeftWidth: 3, borderLeftColor: GOLD },
  quoteMark: { fontSize: 28, color: GOLD, lineHeight: 20, fontWeight: '800' },
  quoteText: { fontSize: 13, color: '#5B5847', fontStyle: 'italic', lineHeight: 19, marginTop: -6 },

  warningBanner: {
    marginTop: 16, padding: 12, borderRadius: 10,
    backgroundColor: AMBER_BG, borderWidth: 1, borderColor: '#EBD9A8',
  },
  warningText: { color: AMBER, fontSize: 12.5, fontWeight: '700', textAlign: 'center' },

  limeSection: { marginTop: 4 },
  reasonRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  reasonDot: { width: 8, height: 8, borderRadius: 4, marginRight: 10 },
  reasonWord: { flex: 1, fontSize: 14, color: INK, fontWeight: '600' },
  reasonWeight: { fontSize: 13, color: MUTED, fontVariant: ['tabular-nums'] },
});