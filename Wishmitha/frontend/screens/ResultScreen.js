import { View, Text, ScrollView, StyleSheet } from 'react-native';

export default function ResultScreen({ route }) {
  const { data } = route.params;
  const isCredible = data.label === 'CREDIBLE';

  return (
    <ScrollView style={s.container}>
      <View style={[s.scoreCard, { backgroundColor: isCredible ? '#E1F5EE' : '#FCEBEB' }]}>
        <Text style={s.scoreLabel}>විශ්වසනීයතා අංකය</Text>
        <Text style={[s.score, { color: isCredible ? '#085041' : '#A32D2D' }]}>
          {(data.final_score * 100).toFixed(0)}%
        </Text>
        <Text style={[s.labelTxt, { color: isCredible ? '#085041' : '#A32D2D' }]}>
          {isCredible ? '✅ විශ්වාසදායකයි' : '⚠️ සැක සහිතයි'}
        </Text>
      </View>

      {data.temporal_warning && (
        <View style={s.warning}>
          <Text style={s.warningText}>⏰ මෙය පැරණි පුවතක් විය හැක</Text>
        </View>
      )}

      <Text style={s.sectionTitle}>LIME — මෙසේ සිතූ හේතු</Text>
      {data.lime_reasons.map((r, i) => (
        <View key={i} style={[s.reason,
          { backgroundColor: r.flag === 'suspicious' ? '#FAEEDA' : '#E1F5EE' }]}>
          <Text style={s.reasonWord}>"{r.word}"</Text>
          <Text style={s.reasonFlag}>
            {r.flag === 'suspicious' ? '⚠️ සැකසහිත' : '✅ විශ්වාසදායක'}
          </Text>
        </View>
      ))}

      <View style={s.scores}>
        <Text style={s.scoresTitle}>Score Breakdown</Text>
        <Text style={s.scoreRow}>Content  : {(data.content_score * 100).toFixed(0)}%</Text>
        <Text style={s.scoreRow}>Source   : {(data.source_score * 100).toFixed(0)}%</Text>
        <Text style={s.scoreRow}>Temporal : {(data.temporal_score * 100).toFixed(0)}%</Text>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  container: { flex:1, backgroundColor:'#f9f9f9', padding:16 },
  scoreCard: { borderRadius:14, padding:24, alignItems:'center', marginBottom:14 },
  scoreLabel: { fontSize:13, color:'#555', marginBottom:4 },
  score: { fontSize:52, fontWeight:'700' },
  labelTxt: { fontSize:18, fontWeight:'600', marginTop:4 },
  warning: { backgroundColor:'#FAEEDA', borderRadius:10, padding:12, marginBottom:14 },
  warningText: { color:'#633806', fontSize:14 },
  sectionTitle: { fontSize:16, fontWeight:'600', color:'#1a1a1a', marginBottom:10 },
  reason: {
    borderRadius:10, padding:12, marginBottom:8,
    flexDirection:'row', justifyContent:'space-between', alignItems:'center'
  },
  reasonWord: { fontSize:14, fontWeight:'500', color:'#1a1a1a' },
  reasonFlag: { fontSize:13, color:'#555' },
  scores: {
    backgroundColor:'#fff', borderRadius:10, padding:14,
    marginTop:8, marginBottom:24, borderWidth:1, borderColor:'#eee'
  },
  scoresTitle: { fontSize:14, fontWeight:'600', marginBottom:8, color:'#1a1a1a' },
  scoreRow: { fontSize:14, color:'#555', marginBottom:4, fontFamily:'monospace' }
});