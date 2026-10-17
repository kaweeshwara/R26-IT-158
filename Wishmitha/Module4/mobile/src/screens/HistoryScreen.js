import React, {useCallback, useState} from 'react';
import {Alert, Pressable, ScrollView, Share, Text, View} from 'react-native';
import {useFocusEffect} from '@react-navigation/native';
import {
  clearHistory, clearStudyResponses, getHistory, getStudyResponses,
} from '../storage';
import {colors, styles} from '../styles';

const csvCell = value => `"${String(value ?? '').replace(/"/g, '""')}"`;

export default function HistoryScreen({navigation}) {
  const [history, setHistory] = useState([]);
  const [studyCount, setStudyCount] = useState(0);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const [records, studyRows] = await Promise.all([getHistory(), getStudyResponses()]);
      setHistory(records);
      setStudyCount(studyRows.length);
      setError('');
    } catch (loadError) {
      setError(`Could not load local history: ${loadError.message}`);
    }
  }, []);

  useFocusEffect(useCallback(() => { refresh(); }, [refresh]));

  async function exportStudyData() {
    try {
      const rows = await getStudyResponses();
      if (!rows.length) {
        setError('There are no research responses to export.');
        return;
      }
      const columns = [
        'participant_id', 'group', 'item_id', 'participant_decision',
        'trust_likert', 'decision_time_seconds', 'recorded_at',
      ];
      const csv = [
        columns.join(','),
        ...rows.map(row => columns.map(column => csvCell(row[column])).join(',')),
      ].join('\n');
      await Share.share({title: 'SinhalaCheck study responses CSV', message: csv});
      setError('');
    } catch (exportError) {
      setError(`Could not export study responses: ${exportError.message}`);
    }
  }

  function confirmClear() {
    Alert.alert('Clear local data?', 'This removes analysis history and research responses from this device.', [
      {text: 'Cancel', style: 'cancel'},
      {text: 'Clear data', style: 'destructive', onPress: async () => {
        try {
          await Promise.all([clearHistory(), clearStudyResponses()]);
          await refresh();
        } catch (clearError) {
          setError(`Could not clear local data: ${clearError.message}`);
        }
      }},
    ]);
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>History</Text>
      <Text style={styles.subtitle}>
        Analysis history and study responses stay on this device until you export or clear them.
      </Text>
      {studyCount > 0 && (
        <View style={styles.card}>
          <Text style={styles.heading}>{studyCount} saved study response(s)</Text>
          <Pressable onPress={exportStudyData} style={styles.button}>
            <Text style={styles.buttonText}>Export anonymous CSV</Text>
          </Pressable>
        </View>
      )}
      {history.length === 0
        ? <Text style={styles.small}>No saved analyses yet.</Text>
        : history.map(record => (
          <Pressable key={record.id} onPress={() => navigation.navigate('Result', {record})}
            style={styles.card}>
            <Text style={styles.heading}>
              {record.result?.verdict || 'Analysis'} · {((record.result?.final_score || 0) * 100).toFixed(1)}%
            </Text>
            <Text numberOfLines={2} style={styles.small}>{record.text}</Text>
            <Text style={styles.small}>{new Date(record.createdAt).toLocaleString()}</Text>
          </Pressable>
        ))}
      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      <Pressable onPress={confirmClear} style={[styles.button, {backgroundColor: colors.danger}]}>
        <Text style={styles.buttonText}>Clear local data</Text>
      </Pressable>
    </ScrollView>
  );
}
