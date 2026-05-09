import { StatusBar } from 'expo-status-bar';
import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import AnalyzeForm from './src/components/AnalyzeForm';
import ErrorBanner from './src/components/ErrorBanner';
import ResultView from './src/components/ResultView';
import { analyze, ApiError } from './src/api/sinhalaCheck';
import { API_BASE_URL } from './src/config';
import { colors, spacing, typography } from './src/theme';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleAnalyze(payload) {
    setLoading(true);
    setError(null);
    try {
      const data = await analyze(payload);
      setResult(data);
    } catch (e) {
      setResult(null);
      if (e instanceof ApiError) {
        setError({ message: e.message, status: e.status });
      } else {
        setError({ message: e?.message || 'Unexpected error', status: 0 });
      }
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setResult(null);
    setError(null);
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="dark" />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.header}>
            <View style={styles.brandRow}>
              <View style={styles.logo}>
                <Text style={styles.logoText}>SC</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={typography.h1}>SinhalaCheck</Text>
                <Text style={[typography.small, { marginTop: 2 }]}>
                  Sri Lankan news credibility · English · සිංහල · Singlish
                </Text>
              </View>
            </View>
            <Text style={styles.apiHint} numberOfLines={1}>
              API: {API_BASE_URL}
            </Text>
          </View>

          <AnalyzeForm
            loading={loading}
            onSubmit={handleAnalyze}
            onReset={handleReset}
            hasResult={!!result}
          />

          <ErrorBanner error={error} onDismiss={() => setError(null)} />

          {result ? <ResultView result={result} /> : null}

          {!result && !error && !loading ? (
            <View style={styles.empty}>
              <Text style={styles.emptyTitle}>How it works</Text>
              <Text style={styles.emptyBody}>
                1. Paste an article URL (or just a domain).{'\n'}
                2. Optionally include the article text — Sinhala, English, or Singlish.{'\n'}
                3. Get a credibility verdict, freshness check, and a breakdown of why.
              </Text>
            </View>
          ) : null}

          <View style={styles.footer}>
            <Text style={typography.tiny}>
              Built with FastAPI · Expo · React Native
            </Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  scroll: {
    padding: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  header: {
    marginBottom: spacing.lg,
    marginTop: spacing.sm,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  logo: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
    shadowColor: colors.primaryDark,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.25,
    shadowRadius: 10,
    elevation: 3,
  },
  logoText: {
    color: '#fff',
    fontWeight: '900',
    fontSize: 16,
    letterSpacing: 0.5,
  },
  apiHint: {
    fontSize: 11,
    color: colors.textFaint,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    marginTop: 2,
  },
  empty: {
    backgroundColor: colors.primarySoft,
    borderRadius: 16,
    padding: spacing.lg,
    marginTop: spacing.sm,
  },
  emptyTitle: {
    color: colors.primaryDark,
    fontWeight: '800',
    marginBottom: 6,
    fontSize: 14,
    letterSpacing: 0.3,
  },
  emptyBody: {
    color: colors.primaryDark,
    fontSize: 13,
    lineHeight: 20,
  },
  footer: {
    alignItems: 'center',
    marginTop: spacing.xl,
  },
});
