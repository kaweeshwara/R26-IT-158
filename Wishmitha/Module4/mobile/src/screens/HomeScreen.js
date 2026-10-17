import React, {useState} from 'react';
import {
  ActivityIndicator, Pressable, ScrollView, Switch, Text, TextInput, View,
} from 'react-native';
import studyItems from '../../assets/study-items.json';
import {API_BASE_URL, analyzeArticle, getApiError} from '../api';
import {saveHistoryRecord} from '../storage';
import {colors, styles} from '../styles';

const RESEARCH_ENABLED =
  process.env.EXPO_PUBLIC_ENABLE_RESEARCH === 'true' &&
  process.env.EXPO_PUBLIC_ETHICS_APPROVED === 'true' &&
  ['A', 'B'].includes(process.env.EXPO_PUBLIC_STUDY_GROUP) &&
  Boolean(process.env.EXPO_PUBLIC_CONSENT_TEXT?.trim());
const RESEARCH_GROUP = process.env.EXPO_PUBLIC_STUDY_GROUP;
const CONSENT_TEXT = process.env.EXPO_PUBLIC_CONSENT_TEXT;

export default function HomeScreen({navigation}) {
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [publishedDate, setPublishedDate] = useState('');
  const [crossCount, setCrossCount] = useState('');
  const [explain, setExplain] = useState(true);
  const [researchMode, setResearchMode] = useState(false);
  const group = RESEARCH_GROUP;
  const [participantCode, setParticipantCode] = useState('');
  const [itemId, setItemId] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);
  const [consented, setConsented] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const willExplain = researchMode ? group === 'B' : explain;

  async function submit() {
    const article = text.trim();
    if (!article) {
      setError('Enter the Sinhala or mixed-language article text first.');
      return;
    }
    if (publishedDate && Number.isNaN(Date.parse(publishedDate))) {
      setError('Enter the publication date as YYYY-MM-DD or an ISO date.');
      return;
    }
    if (crossCount && (!/^\d+$/.test(crossCount) || Number(crossCount) < 0)) {
      setError('The corroborating-source count must be a non-negative whole number.');
      return;
    }
    if (researchMode && (!consented || !participantCode.trim() || !selectedItem)) {
      setError('Research mode requires consent, an anonymous participant code, and a reviewed study item.');
      return;
    }

    setBusy(true);
    setError('');
    try {
      const request = {text: article, explain: researchMode ? group === 'B' : explain};
      if (url.trim()) request.url = url.trim();
      if (publishedDate.trim()) {
        request.published_date = new Date(publishedDate).toISOString();
      }
      if (crossCount) request.cross_count = Number(crossCount);

      const result = await analyzeArticle(request);
      const record = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        createdAt: new Date().toISOString(),
        text: article,
        url: url.trim(),
        explain: request.explain,
        displayGroup: researchMode ? group : null,
        study: researchMode ? {
          participantId: participantCode.trim(),
          itemId: itemId.trim(),
          group,
        } : null,
        result,
      };
      await saveHistoryRecord(record);
      navigation.navigate('Result', {record});
    } catch (requestError) {
      setError(getApiError(requestError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      <Text style={styles.title}>Check a Sinhala news claim</Text>
      <Text style={styles.subtitle}>
        Analyze text and, when available, a source URL. Scores are research outputs, not proof of truth.
      </Text>

      <View style={styles.card}>
        <Text style={styles.label}>Article text or forwarded message *</Text>
        <TextInput
          accessibilityLabel="Article text or forwarded message"
          editable={!researchMode}
          multiline
          onChangeText={setText}
          placeholder="Paste Sinhala news text or a WhatsApp forward..."
          placeholderTextColor="#718198"
          style={[styles.input, styles.multiline]}
          textAlignVertical="top"
          value={text}
        />
        <Text style={styles.label}>Source URL (optional)</Text>
        <TextInput
          autoCapitalize="none"
          autoCorrect={false}
          editable={!researchMode}
          onChangeText={setUrl}
          placeholder="https://news.example.lk/article"
          placeholderTextColor="#718198"
          style={styles.input}
          value={url}
        />
        <Text style={styles.label}>Publication date (optional)</Text>
        <TextInput
          editable={!researchMode}
          onChangeText={setPublishedDate}
          placeholder="YYYY-MM-DD"
          placeholderTextColor="#718198"
          style={styles.input}
          value={publishedDate}
        />
        <Text style={styles.label}>Corroborating sources (optional)</Text>
        <TextInput
          editable={!researchMode}
          keyboardType="number-pad"
          onChangeText={setCrossCount}
          placeholder="e.g. 3"
          placeholderTextColor="#718198"
          style={styles.input}
          value={crossCount}
        />
        {!researchMode && (
          <View style={[styles.row, {marginTop: 18}]}>
            <Switch
              onValueChange={setExplain}
              trackColor={{true: colors.accent}}
              value={explain}
            />
            <Text style={[styles.small, {flex: 1}]}>
              Show score + bilingual LIME explanations and temporal warning (slower)
            </Text>
          </View>
        )}
      </View>

      {RESEARCH_ENABLED && (
        <View style={styles.card}>
          <View style={styles.row}>
            <Switch onValueChange={setResearchMode} value={researchMode} />
            <Text style={styles.heading}>Approved research study mode</Text>
          </View>
          {researchMode && (
            <>
              <Text style={styles.small}>
                Use only under the approved protocol. Do not enter names or contact details.
              </Text>
              {studyItems.length === 0
                ? <Text style={styles.error}>
                  No reviewed study items are installed. Prepare the approved ten-item pack using the research tools.
                </Text>
                : studyItems.map(item => (
                  <Pressable key={item.item_id}
                    onPress={() => {
                      setSelectedItem(item);
                      setItemId(item.item_id);
                      setText(item.text);
                      setUrl(item.url || '');
                      setPublishedDate(item.published_date || '');
                      setError('');
                    }}
                    style={[
                      styles.button,
                      selectedItem?.item_id === item.item_id ? null : styles.secondaryButton,
                    ]}>
                    <Text style={[
                      styles.buttonText,
                      selectedItem?.item_id === item.item_id ? null : styles.secondaryButtonText,
                    ]}>
                      {selectedItem?.item_id === item.item_id ? 'Selected · ' : ''}
                      {item.item_id}
                    </Text>
                  </Pressable>
                ))}
              <Text style={styles.label}>
                Assigned group: {group} · {group === 'A' ? 'Score only' : 'Explanation + temporal warning'}
              </Text>
              <Text style={styles.small}>
                The study facilitator sets the group when building the app; participants cannot change it.
              </Text>
              <Text style={styles.label}>Anonymous participant code</Text>
              <TextInput autoCapitalize="characters" onChangeText={setParticipantCode}
                style={styles.input} value={participantCode} />
              <Text style={styles.label}>Study item ID</Text>
              <Text style={styles.small}>{itemId || 'Select a reviewed item above.'}</Text>
              <View style={[styles.row, {marginTop: 14}]}>
                <Switch onValueChange={setConsented} value={consented} />
                <Text style={[styles.small, {flex: 1}]}>
                  {CONSENT_TEXT}
                </Text>
              </View>
            </>
          )}
        </View>
      )}

      {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      <Pressable accessibilityRole="button" disabled={busy} onPress={submit} style={styles.button}>
        {busy
          ? <View style={styles.row}><ActivityIndicator color="#fff" />
            <Text style={styles.buttonText}> Analysing{willExplain ? ' with LIME' : ''}…</Text></View>
          : <Text style={styles.buttonText}>Analyze</Text>}
      </Pressable>
      <Pressable onPress={() => navigation.navigate('History')}
        style={[styles.button, styles.secondaryButton]}>
        <Text style={[styles.buttonText, styles.secondaryButtonText]}>View local history</Text>
      </Pressable>
      <Text style={[styles.small, {marginTop: 14}]}>API: {API_BASE_URL}</Text>
    </ScrollView>
  );
}
