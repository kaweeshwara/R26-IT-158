import React, { useState, useCallback } from 'react';
import { View, Text, FlatList, StyleSheet, RefreshControl, TouchableOpacity, TextInput, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useFocusEffect } from 'expo-router';

const HISTORY_KEY = 'sinhalacheck_history';
const INK = '#1B2340';
const INDIGO = '#2A3B8F';
const MUTED = '#8B8878';
const BORDER = '#E4E1D8';

type HistoryItem = {
  id: string;
  text: string;
  label: string;
  score: number;
  date: string;
  note?: string;
};

export default function HistoryScreen() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [noteDraft, setNoteDraft] = useState('');

  const loadHistory = async () => {
    try {
      const stored = await AsyncStorage.getItem(HISTORY_KEY);
      setHistory(stored ? JSON.parse(stored) : []);
    } catch (e) {
      console.log('Failed to load history', e);
    }
  };

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

  const deleteItem = async (id: string) => {
    Alert.alert('Delete this entry?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          const updated = history.filter((item) => item.id !== id);
          setHistory(updated);
          await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
        },
      },
    ]);
  };

  const clearAll = async () => {
    Alert.alert('Clear all history?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Clear All',
        style: 'destructive',
        onPress: async () => {
          setHistory([]);
          await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify([]));
        },
      },
    ]);
  };

  const startEditing = (item: HistoryItem) => {
    setEditingId(item.id);
    setNoteDraft(item.note || '');
  };

  const saveNote = async (id: string) => {
    const updated = history.map((item) =>
      item.id === id ? { ...item, note: noteDraft.trim() } : item
    );
    setHistory(updated);
    await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
    setEditingId(null);
    setNoteDraft('');
  };

  const cancelEditing = () => {
    setEditingId(null);
    setNoteDraft('');
  };

  const getColor = (label: string) => {
    if (label === 'CREDIBLE') return '#1F7A5C';
    if (label === 'UNCERTAIN') return '#A6720B';
    return '#B23A3A';
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>Check History</Text>
        {history.length > 0 && (
          <TouchableOpacity onPress={clearAll}>
            <Text style={styles.clearAllText}>Clear All</Text>
          </TouchableOpacity>
        )}
      </View>

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

              {editingId === item.id ? (
                <View style={styles.editRow}>
                  <TextInput
                    style={styles.noteInput}
                    placeholder="Add a personal note..."
                    placeholderTextColor="#B7B4A6"
                    value={noteDraft}
                    onChangeText={setNoteDraft}
                    autoFocus
                  />
                  <View style={styles.editButtonsRow}>
                    <TouchableOpacity onPress={cancelEditing} style={styles.smallBtn}>
                      <Text style={styles.cancelText}>Cancel</Text>
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => saveNote(item.id)} style={[styles.smallBtn, styles.saveBtn]}>
                      <Text style={styles.saveText}>Save</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ) : (
                <>
                  {item.note ? <Text style={styles.noteText}>📝 {item.note}</Text> : null}
                  <View style={styles.actionsRow}>
                    <TouchableOpacity onPress={() => startEditing(item)}>
                      <Text style={styles.actionText}>{item.note ? 'Edit note' : 'Add note'}</Text>
                    </TouchableOpacity>
                    <TouchableOpacity onPress={() => deleteItem(item.id)}>
                      <Text style={styles.deleteText}>Delete</Text>
                    </TouchableOpacity>
                  </View>
                </>
              )}
            </View>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', padding: 20, paddingTop: 60 },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  title: { fontSize: 24, fontWeight: 'bold', color: INDIGO },
  clearAllText: { fontSize: 13, color: '#B23A3A', fontWeight: '600' },
  empty: { fontSize: 14, color: '#666', textAlign: 'center', marginTop: 40 },
  card: { backgroundColor: '#f5f5f5', borderRadius: 10, padding: 14, marginBottom: 12 },
  cardText: { fontSize: 14, color: '#222', marginBottom: 8 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { fontSize: 14, fontWeight: 'bold' },
  score: { fontSize: 14, color: '#333' },
  date: { fontSize: 11, color: '#999', marginTop: 6 },
  noteText: { fontSize: 12, color: '#444', marginTop: 8, fontStyle: 'italic' },
  actionsRow: { flexDirection: 'row', justifyContent: 'flex-end', gap: 16, marginTop: 10 },
  actionText: { fontSize: 12, color: INDIGO, fontWeight: '600' },
  deleteText: { fontSize: 12, color: '#B23A3A', fontWeight: '600' },
  editRow: { marginTop: 10 },
  noteInput: { borderWidth: 1, borderColor: BORDER, borderRadius: 8, padding: 8, fontSize: 13, backgroundColor: '#fff' },
  editButtonsRow: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 8 },
  smallBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  saveBtn: { backgroundColor: INDIGO },
  cancelText: { fontSize: 12, color: MUTED, fontWeight: '600' },
  saveText: { fontSize: 12, color: '#fff', fontWeight: '600' },
});