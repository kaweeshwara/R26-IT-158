import React, { useState, useCallback } from 'react';
import { View, Text, FlatList, StyleSheet, RefreshControl } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useFocusEffect } from 'expo-router';

const HISTORY_KEY = 'sinhalacheck_history';

type HistoryItem = {
  id: string;
  text: string;
  label: string;
  score: number;
  date: string;
};

export default function HistoryScreen() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const loadHistory = async () => {
    try {
      const stored = await AsyncStorage.getItem(HISTORY_KEY);
      setHistory(stored ? JSON.parse(stored) : []);
    } catch (e) {
      console.log('Failed to load history', e);
    }
  };

  // Reload every time this tab is opened
  useFocusEffect(
    useCallback(() => {
      loadHistory();
    }, [])
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await loadHistory();
    setRefreshing(false);
  };

  const getColor = (label: string) => {
    if (label === 'CREDIBLE') return '#0F6B57';
    if (label === 'UNCERTAIN') return '#8A5A00';
    return '#9B1C1C';
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Check History</Text>
      {history.length === 0 ? (
        <Text style={styles.empty}>No checks yet. Go to Home and check some text!</Text>
      ) : (
        <FlatList
          data={history}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <Text style={styles.cardText} numberOfLines={2}>{item.text}</Text>
              <View style={styles.cardFooter}>
                <Text style={[styles.label, { color: getColor(item.label) }]}>{item.label}</Text>
                <Text style={styles.score}>{item.score}</Text>
              </View>
              <Text style={styles.date}>{item.date}</Text>
            </View>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', padding: 20, paddingTop: 60 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#1F3864', marginBottom: 16 },
  empty: { fontSize: 14, color: '#666', textAlign: 'center', marginTop: 40 },
  card: { backgroundColor: '#f5f5f5', borderRadius: 10, padding: 14, marginBottom: 12 },
  cardText: { fontSize: 14, color: '#222', marginBottom: 8 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { fontSize: 14, fontWeight: 'bold' },
  score: { fontSize: 14, color: '#333' },
  date: { fontSize: 11, color: '#999', marginTop: 6 },
});