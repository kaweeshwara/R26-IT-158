import React, { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import Card from './Card';
import { colors, radius, spacing, typography } from '../theme';

const DATE_PLACEHOLDER = 'YYYY-MM-DD or 2026-04-01T08:30:00Z';

export default function AnalyzeForm({ loading, onSubmit, onReset, hasResult }) {
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [publishedDate, setPublishedDate] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [crossCount, setCrossCount] = useState('');
  const [seenCount, setSeenCount] = useState('');
  const [recirculated, setRecirculated] = useState(false);
  const [recirculatedSet, setRecirculatedSet] = useState(false);
  const [validation, setValidation] = useState(null);

  function handleSubmit() {
    const cleanedUrl = url.trim();
    if (!cleanedUrl) {
      setValidation('Please enter an article URL or domain.');
      return;
    }
    setValidation(null);

    const payload = { url: cleanedUrl };
    if (text.trim()) payload.text = text.trim();
    if (publishedDate.trim()) payload.published_date = normalizeDate(publishedDate.trim());

    if (crossCount.trim()) {
      const n = parseInt(crossCount, 10);
      if (!Number.isNaN(n) && n >= 0) payload.cross_count = n;
    }
    if (seenCount.trim()) {
      const n = parseInt(seenCount, 10);
      if (!Number.isNaN(n) && n >= 0) payload.seen_count = n;
    }
    if (recirculatedSet) payload.recirculated = recirculated;

    onSubmit(payload);
  }

  function handleClear() {
    setUrl('');
    setText('');
    setPublishedDate('');
    setCrossCount('');
    setSeenCount('');
    setRecirculated(false);
    setRecirculatedSet(false);
    setValidation(null);
    onReset?.();
  }

  return (
    <Card>
      <Text style={typography.h2}>Check an article</Text>
      <Text style={[typography.small, { marginTop: 4, marginBottom: spacing.lg }]}>
        Paste a URL or domain. You can include the article text in English, Sinhala, or Singlish.
      </Text>

      <Field label="Article URL or domain" required>
        <TextInput
          value={url}
          onChangeText={setUrl}
          placeholder="https://www.adaderana.lk/news/123/sample"
          placeholderTextColor={colors.textFaint}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
          style={styles.input}
          editable={!loading}
        />
      </Field>

      <Field label="Article text or claim (optional)">
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder="කොළඹ දී අද සිදුවූ සිදුවීම... / Breaking: ..."
          placeholderTextColor={colors.textFaint}
          multiline
          numberOfLines={4}
          textAlignVertical="top"
          style={[styles.input, styles.textarea]}
          editable={!loading}
        />
      </Field>

      <Field label="Published date (optional)">
        <TextInput
          value={publishedDate}
          onChangeText={setPublishedDate}
          placeholder={DATE_PLACEHOLDER}
          placeholderTextColor={colors.textFaint}
          autoCapitalize="none"
          autoCorrect={false}
          style={styles.input}
          editable={!loading}
        />
      </Field>

      <Pressable
        onPress={() => setShowAdvanced((v) => !v)}
        style={styles.advancedToggle}
        hitSlop={8}
      >
        <Text style={styles.advancedToggleText}>
          {showAdvanced ? '− Hide advanced' : '+ Show advanced'}
        </Text>
      </Pressable>

      {showAdvanced ? (
        <View style={styles.advanced}>
          <View style={styles.row}>
            <View style={[styles.col, { marginRight: spacing.sm }]}>
              <Field label="Cross sources (≥0)">
                <TextInput
                  value={crossCount}
                  onChangeText={(v) => setCrossCount(v.replace(/[^0-9]/g, ''))}
                  placeholder="3"
                  placeholderTextColor={colors.textFaint}
                  keyboardType="number-pad"
                  style={styles.input}
                  editable={!loading}
                />
              </Field>
            </View>
            <View style={[styles.col, { marginLeft: spacing.sm }]}>
              <Field label="Seen count (≥0)">
                <TextInput
                  value={seenCount}
                  onChangeText={(v) => setSeenCount(v.replace(/[^0-9]/g, ''))}
                  placeholder="0"
                  placeholderTextColor={colors.textFaint}
                  keyboardType="number-pad"
                  style={styles.input}
                  editable={!loading}
                />
              </Field>
            </View>
          </View>

          <View style={styles.switchRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>Mark as recirculated</Text>
              <Text style={typography.small}>
                Override if you know the article was republished.
              </Text>
            </View>
            <Switch
              value={recirculated}
              onValueChange={(v) => {
                setRecirculated(v);
                setRecirculatedSet(true);
              }}
              disabled={loading}
              trackColor={{ true: colors.primary, false: colors.border }}
              thumbColor="#fff"
            />
          </View>
          {recirculatedSet ? (
            <Pressable onPress={() => setRecirculatedSet(false)} hitSlop={8}>
              <Text style={styles.clearOverride}>Clear override</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}

      {validation ? <Text style={styles.error}>{validation}</Text> : null}

      <View style={styles.actions}>
        <Pressable
          onPress={handleSubmit}
          disabled={loading}
          style={({ pressed }) => [
            styles.submit,
            (pressed || loading) && styles.submitPressed,
          ]}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.submitText}>Analyze</Text>
          )}
        </Pressable>

        {(hasResult || url || text || publishedDate) && !loading ? (
          <Pressable onPress={handleClear} style={styles.secondary} hitSlop={8}>
            <Text style={styles.secondaryText}>Clear</Text>
          </Pressable>
        ) : null}
      </View>
    </Card>
  );
}

function Field({ label, required, children }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>
        {label}
        {required ? <Text style={{ color: colors.risky }}> *</Text> : null}
      </Text>
      {children}
    </View>
  );
}

function normalizeDate(input) {
  if (!input) return input;
  if (/^\d{4}-\d{2}-\d{2}$/.test(input)) return `${input}T00:00:00Z`;
  return input;
}

const styles = StyleSheet.create({
  field: { marginBottom: spacing.md },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.textMuted,
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontSize: 15,
    color: colors.text,
    backgroundColor: '#fff',
  },
  textarea: { minHeight: 96, paddingTop: 10 },
  advancedToggle: { paddingVertical: spacing.sm, alignSelf: 'flex-start' },
  advancedToggleText: { color: colors.primary, fontWeight: '700', fontSize: 13 },
  advanced: {
    backgroundColor: colors.cardAlt,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  row: { flexDirection: 'row' },
  col: { flex: 1 },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: spacing.sm,
  },
  clearOverride: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: '600',
    marginTop: 6,
  },
  error: {
    color: colors.risky,
    fontSize: 13,
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  actions: { flexDirection: 'row', alignItems: 'center', marginTop: spacing.md },
  submit: {
    flex: 1,
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colors.primaryDark,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.18,
    shadowRadius: 10,
    elevation: 2,
  },
  submitPressed: { opacity: 0.85 },
  submitText: { color: '#fff', fontWeight: '700', fontSize: 16, letterSpacing: 0.3 },
  secondary: {
    paddingHorizontal: spacing.lg,
    paddingVertical: 14,
    marginLeft: spacing.sm,
  },
  secondaryText: { color: colors.textMuted, fontWeight: '600' },
});
