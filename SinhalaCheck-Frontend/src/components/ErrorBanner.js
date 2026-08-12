import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../theme';

export default function ErrorBanner({ error, onDismiss }) {
  if (!error) return null;
  const message = typeof error === 'string' ? error : error?.message || 'Something went wrong.';
  const status = typeof error === 'object' ? error?.status : null;
  return (
    <View style={styles.box}>
      <View style={{ flex: 1 }}>
        <Text style={styles.title}>
          {status ? `Error ${status}` : 'Could not analyze'}
        </Text>
        <Text style={styles.body}>{message}</Text>
      </View>
      {onDismiss ? (
        <Pressable onPress={onDismiss} hitSlop={10}>
          <Text style={styles.close}>×</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: colors.riskySoft,
    borderColor: colors.risky,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  title: { color: colors.risky, fontWeight: '800', marginBottom: 4 },
  body: { color: colors.risky, fontSize: 13, lineHeight: 18 },
  close: { color: colors.risky, fontSize: 22, marginLeft: spacing.md, lineHeight: 22 },
});
