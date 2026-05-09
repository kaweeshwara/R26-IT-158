import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, Alert
} from 'react-native';
import axios from 'axios';

const API_URL = 'http://192.168.8.151:8000/fuse';

export default function HomeScreen({ navigation }) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);

  const checkNews = async () => {
    if (!text.trim()) { Alert.alert('Error', 'Text type කරන්න'); return; }
    setLoading(true);
    try {
      const res = await axios.post(API_URL, { text });
      navigation.navigate('Result', { data: res.data });
    } catch (e) {
      Alert.alert('Error', 'API connect නොවුනා — uvicorn run වෙනවාද check කරන්න');
    }
    setLoading(false);
  };

  return (
    <View style={s.container}>
      <Text style={s.title}>සිංහල පුවත් පරීක්ෂා කරන්න</Text>
      <TextInput
        style={s.input}
        placeholder="පුවත් text මෙතැන paste කරන්න..."
        value={text}
        onChangeText={setText}
        multiline
        numberOfLines={6}
      />
      <TouchableOpacity style={s.btn} onPress={checkNews} disabled={loading}>
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={s.btnText}>පරීක්ෂා කරන්න</Text>}
      </TouchableOpacity>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex:1, padding:20, backgroundColor:'#f9f9f9' },
  title: { fontSize:20, fontWeight:'600', marginBottom:16, color:'#1a1a1a' },
  input: {
    backgroundColor:'#fff', borderWidth:1, borderColor:'#ddd',
    borderRadius:10, padding:14, fontSize:15,
    minHeight:140, textAlignVertical:'top', marginBottom:16
  },
  btn: { backgroundColor:'#534AB7', borderRadius:10, padding:16, alignItems:'center' },
  btnText: { color:'#fff', fontSize:16, fontWeight:'600' }
});