import React from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import Badge from './Badge';
import Card from './Card';
import { alertTone, colors, radius, spacing, tierTone, timeTone, typography } from '../theme';

export default function HistoryView({
  items,
  loading,
  onOpen,
  onDelete,
  onClearAll,
}) {
  if (loading) {
    return (
      <Card>
        <View style={styles.centered}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[typography.small, { marginTop: spacing.sm }]}>Loading history…</Text>
        </View>
      </Card>
    );
  }

  if (!items.length) {
    return (
      <Card>
        <Text style={typography.h2}>Check history</Text>
        <Text style={[typography.small, { marginTop: spacing.sm }]}>
          Successful analyses will appear here so you can reopen them later.
        </Text>
        <View style={styles.emptyBox}>
          <Text style={styles.emptyTitle}>No checks yet</Text>
          <Text style={styles.emptyBody}>
            Analyze an article on the Check tab. Each result is saved on this device.
          </Text>
        </View>
      </Card>
    );
  }

  return (
    <View>
      <Card>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={typography.h2}>Check history</Text>
            <Text style={[typography.small, { marginTop: 4 }]}>
              {items.length} saved check{items.length === 1 ? '' : 's'} on this device
            </Text>
          </View>
          <Pressable
            onPress={() => {
              Alert.alert(
                'Clear history?',
                'This removes all saved checks from this device.',
                [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Clear all', style: 'destructive', onPress: onClearAll },
                ],
              );
            }}
            hitSlop={8}
            style={styles.clearBtn}
          >
            <Text style={styles.clearBtnText}>Clear all</Text>
          </Pressable>
        </View>
      </Card>

      {items.map((item) => (
        <HistoryItem
          key={item.id}
          item={item}
          onOpen={() => onOpen(item)}
          onDelete={() => {
            Alert.alert('Delete this check?', item.url || 'Remove from history', [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Delete', style: 'destructive', onPress: () => onDelete(item.id) },
            ]);
          }}
        />
      ))}
    </View>
  );
}

function HistoryItem({ item, onOpen, onDelete }) {
  const result = item.result || {};
  const tone = alertTone(result.source_label, result.source_score);
  const tier = tierTone(result.source_tier || result.source_label);
  const timeBadge = timeTone(result.time_label);
  const scorePct =
    typeof result.source_score === 'number'
      ? Math.round(Math.max(0, Math.min(1, result.source_score)) * 100)
      : null;

  return (
    <Card style={styles.itemCard}>
      <Pressable onPress={onOpen} style={({ pressed }) => pressed && styles.pressed}>
        <View style={styles.itemTop}>
          <Text style={styles.when}>{formatCheckedAt(item.checkedAt)}</Text>
          {scorePct !== null ? (
            <Text style={[styles.score, { color: tone.fg }]}>{scorePct}%</Text>
          ) : null}
        </View>

        <Text style={styles.verdict} numberOfLines={2}>
          {result.alert || result.source_label || 'Saved result'}
        </Text>

        <Text style={styles.url} numberOfLines={2}>
          {item.url || 'No URL'}
        </Text>

        {(result.publisher || result.domain) ? (
          <Text style={styles.meta} numberOfLines={1}>
            {[result.publisher, result.domain].filter(Boolean).join(' · ')}
          </Text>
        ) : null}

        {item.textPreview ? (
          <Text style={styles.preview} numberOfLines={2}>
            {item.textPreview}
          </Text>
        ) : null}

        <View style={styles.badges}>
          <Badge label={result.source_label} fg={tier.fg} bg={tier.bg} />
          {result.time_label ? (
            <Badge label={result.time_label} fg={timeBadge.fg} bg={timeBadge.bg} icon="◷" />
          ) : null}
        </View>
      </Pressable>

      <View style={styles.actions}>
        <Pressable onPress={onOpen} style={styles.openBtn} hitSlop={6}>
          <Text style={styles.openBtnText}>Open result</Text>
        </Pressable>
        <Pressable onPress={onDelete} style={styles.deleteBtn} hitSlop={6}>
          <Text style={styles.deleteBtnText}>Delete</Text>
        </Pressable>
      </View>
    </Card>
  );
}

function formatCheckedAt(iso) {
  if (!iso) return 'Unknown time';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'Unknown time';

  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();

  const time = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  if (sameDay) return `Today · ${time}`;

  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const isYesterday =
    d.getFullYear() === yesterday.getFullYear() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getDate() === yesterday.getDate();
  if (isYesterday) return `Yesterday · ${time}`;

  return `${d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })} · ${time}`;
}

const styles = StyleSheet.create({
  centered: { alignItems: 'center', paddingVertical: spacing.xl },
  emptyBox: {
    backgroundColor: colors.primarySoft,
    borderRadius: radius.md,
    padding: spacing.lg,
    marginTop: spacing.lg,
  },
  emptyTitle: {
    color: colors.primaryDark,
    fontWeight: '800',
    fontSize: 14,
    marginBottom: 6,
  },
  emptyBody: {
    color: colors.primaryDark,
    fontSize: 13,
    lineHeight: 20,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  clearBtn: {
    paddingVertical: 6,
    paddingHorizontal: spacing.sm,
  },
  clearBtnText: {
    color: colors.risky,
    fontWeight: '700',
    fontSize: 13,
  },
  itemCard: {
    paddingBottom: spacing.md,
  },
  pressed: { opacity: 0.85 },
  itemTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  when: {
    fontSize: 12,
    color: colors.textFaint,
    fontWeight: '600',
  },
  score: {
    fontSize: 16,
    fontWeight: '800',
  },
  verdict: {
    ...typography.h3,
    marginBottom: 4,
  },
  url: {
    fontSize: 13,
    color: colors.textMuted,
    lineHeight: 18,
  },
  meta: {
    marginTop: 4,
    fontSize: 12,
    color: colors.textFaint,
    fontWeight: '600',
  },
  preview: {
    marginTop: spacing.sm,
    fontSize: 13,
    color: colors.textMuted,
    lineHeight: 18,
    fontStyle: 'italic',
  },
  badges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
  },
  openBtn: {
    flex: 1,
    paddingVertical: 8,
  },
  openBtnText: {
    color: colors.primary,
    fontWeight: '700',
    fontSize: 13,
  },
  deleteBtn: {
    paddingVertical: 8,
    paddingHorizontal: spacing.sm,
  },
  deleteBtnText: {
    color: colors.risky,
    fontWeight: '600',
    fontSize: 13,
  },
});
