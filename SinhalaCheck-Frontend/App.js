import { StatusBar } from 'expo-status-bar';
import React, { useCallback, useEffect, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import AnalyzeForm from './src/components/AnalyzeForm';
import ErrorBanner from './src/components/ErrorBanner';
import HistoryView from './src/components/HistoryView';
import ResultView from './src/components/ResultView';
import { analyze, ApiError } from './src/api/sinhalaCheck';
import { API_BASE_URL } from './src/config';
import {
  addHistoryEntry,
  clearHistory,
  loadHistory,
  removeHistoryEntry,
} from './src/history/storage';
import { colors, radius, spacing, typography } from './src/theme';

export default function App() {
  const [screen, setScreen] = useState('check'); // 'check' | 'history'
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);

  const refreshHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const items = await loadHistory();
      setHistory(items);
      setHistoryCount(items.length);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory().then((items) => setHistoryCount(items.length));
  }, []);

  useEffect(() => {
    if (screen === 'history') {
      refreshHistory();
    }
  }, [screen, refreshHistory]);

  async function handleAnalyze(payload) {
    setLoading(true);
    setError(null);
    try {
      const data = await analyze(payload);
      setResult(data);
      try {
        const items = await addHistoryEntry({
          url: payload.url,
          text: payload.text,
          result: data,
        });
        setHistoryCount(items.length);
        if (screen === 'history') setHistory(items);
      } catch {
        // History is best-effort; don't block the verdict UI.
      }
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

  function handleOpenHistoryItem(item) {
    setResult(item.result || null);
    setError(null);
    setScreen('check');
  }

  async function handleDeleteHistoryItem(id) {
    const items = await removeHistoryEntry(id);
    setHistory(items);
    setHistoryCount(items.length);
  }

  async function handleClearHistory() {
    const items = await clearHistory();
    setHistory(items);
    setHistoryCount(0);
  }

  return (
    <SafeAreaProvider>
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

          <View style={styles.tabs}>
            <TabButton
              label="Check"
              active={screen === 'check'}
              onPress={() => setScreen('check')}
            />
            <TabButton
              label="History"
              active={screen === 'history'}
              badge={historyCount > 0 ? String(historyCount) : null}
              onPress={() => setScreen('history')}
            />
          </View>

          {screen === 'check' ? (
            <>
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
                    2. Optionally include the article text — Sinhala, English, or
                    Singlish.{'\n'}
                    3. Get a credibility verdict, freshness check, and a breakdown of
                    why.{'\n'}
                    4. Reopen past checks anytime from the History tab.
                  </Text>
                </View>
              ) : null}
            </>
          ) : (
            <HistoryView
              items={history}
              loading={historyLoading}
              onOpen={handleOpenHistoryItem}
              onDelete={handleDeleteHistoryItem}
              onClearAll={handleClearHistory}
            />
          )}

          <View style={styles.footer}>
            <Text style={typography.tiny}>
              Built with FastAPI · Expo · React Native
            </Text>
          </View>
        </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

function TabButton({ label, active, badge, onPress }) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.tab, active && styles.tabActive]}
      accessibilityRole="tab"
      accessibilityState={{ selected: active }}
    >
      <Text style={[styles.tabText, active && styles.tabTextActive]}>{label}</Text>
      {badge ? (
        <View style={[styles.badge, active && styles.badgeActive]}>
          <Text style={[styles.badgeText, active && styles.badgeTextActive]}>{badge}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  scroll: {
    padding: spacing.lg,
    paddingBottom: spacing.xxl,
  },
  header: {
    marginBottom: spacing.md,
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
  tabs: {
    flexDirection: 'row',
    backgroundColor: colors.cardAlt,
    borderRadius: radius.md,
    padding: 4,
    marginBottom: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: radius.sm,
  },
  tabActive: {
    backgroundColor: colors.card,
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 1,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.textMuted,
  },
  tabTextActive: {
    color: colors.primaryDark,
  },
  badge: {
    marginLeft: 6,
    minWidth: 20,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: radius.pill,
    backgroundColor: colors.neutralSoft,
    alignItems: 'center',
  },
  badgeActive: {
    backgroundColor: colors.primarySoft,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '800',
    color: colors.textMuted,
  },
  badgeTextActive: {
    color: colors.primaryDark,
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
