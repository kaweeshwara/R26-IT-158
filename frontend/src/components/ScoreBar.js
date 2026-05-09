import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing } from '../theme';

export default function ScoreBar({ label, value, color = colors.primary, suffix = '%' }) {
  const v = clamp(typeof value === 'number' ? value : 0, 0, 1);
  const pct = Math.round(v * 100);
  return (
    <View style={styles.row}>
      <View style={styles.header}>
        <Text style={styles.label} numberOfLines={1}>
          {label}
        </Text>
        <Text style={[styles.value, { color }]}>
          {pct}
          {suffix}
        </Text>
      </View>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${pct}%`, backgroundColor: color }]} />
      </View>
    </View>
  );
}

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n));
}

const styles = StyleSheet.create({
  row: { marginBottom: spacing.md },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  label: { fontSize: 13, color: colors.textMuted, flex: 1, paddingRight: spacing.sm },
  value: { fontSize: 13, fontWeight: '700' },
  track: {
    height: 8,
    borderRadius: radius.pill,
    backgroundColor: colors.cardAlt,
    overflow: 'hidden',
  },
  fill: { height: '100%', borderRadius: radius.pill },
});
