import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, Switch, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useFocusEffect } from 'expo-router';

const SETTINGS_KEY = 'sinhalacheck_settings';
const HISTORY_KEY = 'sinhalacheck_history';
const INDIGO = '#2A3B8F';
const MUTED = '#8B8878';
const BORDER = '#E4E1D8';
const PAPER = '#F7F5F0';

export default function SettingsScreen() {
  const [showLime, setShowLime] = useState(true);
  const [fontScale, setFontScale] = useState(false); // false = normal, true = large

  const loadSettings = async () => {
    try {
      const stored = await AsyncStorage.getItem(SETTINGS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setShowLime(parsed.showLime ?? true);
        setFontScale(parsed.fontScale ?? false);
      }
    } catch (e) {
      console.log('Failed to load settings', e);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadSettings();
    }, [])
  );

  const saveSettings = async (updates: any) => {
    const current = { showLime, fontScale, ...updates };
    setShowLime(current.showLime);
    setFontScale(current.fontScale);
    await AsyncStorage.setItem(SETTINGS_KEY, JSON.stringify(current));
  };

  const clearAllHistory = () => {
    Alert.alert('Clear all history?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Clear',
        style: 'destructive',
        onPress: async () => {
          await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify([]));
          Alert.alert('Done', 'History cleared.');
        },
      },
    ]);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Settings</Text>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>RESEARCH / USER STUDY</Text>

        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text style={styles.rowTitle}>Show LIME Explanations</Text>
            <Text style={styles.rowDesc}>
              ON = Version B (score + explanations). OFF = Version A (score only).
            </Text>
          </View>
          <Switch
            value={showLime}
            onValueChange={(val) => saveSettings({ showLime: val })}
            trackColor={{ false: '#ccc', true: INDIGO }}
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>ACCESSIBILITY</Text>

        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text style={styles.rowTitle}>Large Text</Text>
            <Text style={styles.rowDesc}>Increase font size across the app.</Text>
          </View>
          <Switch
            value={fontScale}
            onValueChange={(val) => saveSettings({ fontScale: val })}
            trackColor={{ false: '#ccc', true: INDIGO }}
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionLabel}>DATA</Text>
        <View style={styles.row}>
          <Text style={[styles.rowTitle, { color: '#B23A3A' }]} onPress={clearAllHistory}>
            Clear All History
          </Text>
        </View>
      </View>

      <Text style={styles.footer}>SinhalaCheck v1.0 — Module 3 Research Prototype</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: PAPER, padding: 20, paddingTop: 60 },
  title: { fontSize: 24, fontWeight: 'bold', color: INDIGO, marginBottom: 24 },
  section: {
    backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 16,
    borderWidth: 1, borderColor: BORDER,
  },
  sectionLabel: { fontSize: 11, fontWeight: '700', color: MUTED, letterSpacing: 1, marginBottom: 12 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 8 },
  rowTitle: { fontSize: 15, fontWeight: '600', color: '#1B2340' },
  rowDesc: { fontSize: 12, color: MUTED, marginTop: 4, lineHeight: 16 },
  footer: { textAlign: 'center', color: MUTED, fontSize: 11, marginTop: 20 },
});