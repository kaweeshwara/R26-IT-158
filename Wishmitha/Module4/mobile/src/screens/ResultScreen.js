import React, {useRef, useState} from 'react';
import {Pressable, ScrollView, Text, View} from 'react-native';
import {saveStudyResponse} from '../storage';
import {colors, styles} from '../styles';

const DECISIONS = ['CREDIBLE', 'UNCERTAIN', 'MISINFORMATION'];

export default function ResultScreen({route, navigation}) {
  const {record} = route.params;
  const result = record.result;
  const studyStart = useRef(Date.now());
  const [decision, setDecision] = useState('');
  const [trust, setTrust] = useState(4);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const group = record.displayGroup;
  const enhanced = group ? group === 'B' : record.explain;
  const temporal = result.temporal_warning;

  async function saveResponse() {
    if (!decision) {
      setError('Select your decision before saving this study response.');
      return;
    }
    try {
      await saveStudyResponse({
        participant_id: record.study.participantId,
        group: record.study.group,
        item_id: record.study.itemId,
        participant_decision: decision,
        trust_likert: trust,
        decision_time_seconds: Number(((Date.now() - studyStart.current) / 1000).toFixed(2)),
        recorded_at: new Date().toISOString(),
      });
      setSaved(true);
      setError('');
    } catch (saveError) {
      setError(`Could not save the response locally: ${saveError.message}`);
    }
  }

  const verdictColor = result.verdict === 'CREDIBLE'
    ? colors.success
    : result.verdict === 'UNCERTAIN' ? '#8a5a00' : colors.danger;

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.card}>
        <Text style={styles.small}>Fused credibility score</Text>
        <Text style={styles.score}>{(result.final_score * 100).toFixed(1)}%</Text>
        <Text style={[styles.verdict, {color: verdictColor}]}>{result.verdict}</Text>
        {enhanced && !result.weights_provenance?.is_fitted && (
          <Text style={[styles.small, {marginTop: 10, color: '#8a5a00'}]}>
            Fusion weights are unfitted placeholders; treat the combined score as provisional.
          </Text>
        )}
      </View>

      {enhanced && (
        <>
          <View style={styles.card}>
            <Text style={styles.heading}>Signal breakdown</Text>
            {Object.entries(result.breakdown || {}).map(([name, value]) => (
              <Text key={name} style={styles.small}>
                {name}: {value === null ? 'not available' : `${(value * 100).toFixed(1)}%`}
              </Text>
            ))}
          </View>

          <View style={styles.card}>
            <Text style={styles.heading}>Temporal warning</Text>
            {temporal?.available
              ? <Text style={styles.small}>
                {temporal.alert || temporal.freshness_label || 'Freshness assessed'}
                {temporal.age_days !== null && temporal.age_days !== undefined
                  ? ` · ${temporal.age_days} days old` : ''}
                {temporal.recirculated ? ' · Recirculated' : ''}
              </Text>
              : <Text style={styles.small}>
                {temporal?.message || 'No source URL; freshness was not assessed.'}
              </Text>}
          </View>

          {!!result.lime_explanations?.length && (
            <View style={styles.card}>
              <Text style={styles.heading}>LIME explanations · English / සිංහල</Text>
              <Text style={styles.small}>
                These explain the Module 1 content-model prediction. Source and temporal signals
                are shown separately and are not attributed to these words.
              </Text>
              {result.lime_explanations.slice(0, 5).map((item, index) => (
                <View key={`${item.word}-${index}`} style={{marginTop: 12}}>
                  <Text style={[styles.small, {fontWeight: '700', color: colors.ink}]}>
                    {item.word} · {item.weight > 0 ? '+' : ''}{item.weight}
                  </Text>
                  <Text style={styles.small}>{item.english}</Text>
                  <Text style={styles.small}>{item.sinhala}</Text>
                </View>
              ))}
            </View>
          )}

          {!!result.reasons?.length && (
            <View style={styles.card}>
              <Text style={styles.heading}>Analysis notes</Text>
              {result.reasons.map((reason, index) => (
                <Text key={`${index}-${reason}`} style={styles.small}>• {reason}</Text>
              ))}
            </View>
          )}
        </>
      )}

      {record.study && (
        <View style={styles.card}>
          <Text style={styles.heading}>Research response</Text>
          <Text style={styles.small}>
            Item {record.study.itemId} · Group {record.study.group}. Choose your decision and trust rating.
          </Text>
          {DECISIONS.map(value => (
            <Pressable key={value}
              onPress={() => { setDecision(value); setError(''); }}
              style={[styles.button, decision === value ? null : styles.secondaryButton]}>
              <Text style={[
                styles.buttonText, decision === value ? null : styles.secondaryButtonText,
              ]}>{value}</Text>
            </Pressable>
          ))}
          <Text style={styles.label}>How much do you trust this assessment? (1–7)</Text>
          <View style={[styles.row, {flexWrap: 'wrap'}]}>
            {[1, 2, 3, 4, 5, 6, 7].map(value => (
              <Pressable key={value} onPress={() => setTrust(value)}
                style={[styles.button, {minWidth: 40, flex: 1},
                  trust === value ? null : styles.secondaryButton]}>
                <Text style={[
                  styles.buttonText, trust === value ? null : styles.secondaryButtonText,
                ]}>{value}</Text>
              </Pressable>
            ))}
          </View>
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Pressable disabled={saved} onPress={saveResponse}
            style={[styles.button, saved ? styles.secondaryButton : null]}>
            <Text style={[styles.buttonText, saved ? styles.secondaryButtonText : null]}>
              {saved ? 'Response saved on this device' : 'Save anonymous study response'}
            </Text>
          </Pressable>
          {saved && <Text style={styles.small}>
            Decision time was recorded from when this result opened. Export responses from History.
          </Text>}
        </View>
      )}

      <Pressable onPress={() => navigation.navigate('Home')} style={styles.button}>
        <Text style={styles.buttonText}>Analyze another item</Text>
      </Pressable>
    </ScrollView>
  );
}
