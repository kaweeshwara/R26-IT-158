import React from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import {StatusBar} from 'expo-status-bar';
import HomeScreen from './src/screens/HomeScreen';
import ResultScreen from './src/screens/ResultScreen';
import HistoryScreen from './src/screens/HistoryScreen';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="dark" />
      <Stack.Navigator
        initialRouteName="Home"
        screenOptions={{
          headerStyle: {backgroundColor: '#f4f7fb'},
          headerTintColor: '#172b4d',
          contentStyle: {backgroundColor: '#f4f7fb'},
        }}>
        <Stack.Screen name="Home" component={HomeScreen} options={{title: 'SinhalaCheck'}} />
        <Stack.Screen name="Result" component={ResultScreen} options={{title: 'Analysis result'}} />
        <Stack.Screen name="History" component={HistoryScreen} options={{title: 'Local history'}} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
