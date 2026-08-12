import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../theme';

export default function Badge({ label, fg = colors.neutral, bg = colors.neutralSoft, icon }) {
  if (!label) return null;
  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      {icon ? <Text style={[styles.icon, { color: fg }]}>{icon}</Text> : null}
      <Text style={[styles.text, { color: fg }]} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
    borderRadius: radius.pill,
    alignSelf: 'flex-start',
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  text: { fontSize: 12, fontWeight: '700', letterSpacing: 0.3 },
  icon: { fontSize: 12, fontWeight: '700', marginRight: 6 },
});
