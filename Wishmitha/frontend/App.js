import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import HomeScreen from './screens/HomeScreen';
import ResultScreen from './screens/ResultScreen';

const Stack = createNativeStackNavigator();

export default function App() {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={HomeScreen}
          options={{ title: 'SinhalaCheck' }} />
        <Stack.Screen name="Result" component={ResultScreen}
          options={{ title: 'ප්‍රතිඵලය' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}