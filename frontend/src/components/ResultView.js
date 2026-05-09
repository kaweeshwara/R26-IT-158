import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Badge from './Badge';
import Card from './Card';
import ScoreBar from './ScoreBar';
import { alertTone, colors, radius, spacing, tierTone, timeTone, typography } from '../theme';

const BREAKDOWN_LABELS = {
  registration: 'Registration',
  domain_age: 'Domain age',
  history: 'History',
  editorial: 'Editorial',
  cross: 'Cross-coverage',
};

const LANG_LABEL = {
  sinhala: 'Detected: Sinhala',
  singlish: 'Detected: Singlish',
  english: 'Detected: English',
  unknown: 'Language: unknown',
};

export default function ResultView({ result }) {
  const [showDetails, setShowDetails] = useState(false);
  if (!result) return null;

  const tone = alertTone(result.source_label, result.source_score);
  const sourcePct = toPct(result.source_score);
  const tempPct = toPct(result.temporal_score);
  const confidencePct = toPct(result.confidence);

  const ageText = formatAge(result.age_days);
  const tier = tierTone(result.source_tier || result.source_label);
  const timeBadge = timeTone(result.time_label);

  return (
    <View>
      {/* Verdict banner */}
      <View style={[styles.banner, { backgroundColor: tone.bg, borderColor: tone.fg }]}>
        <Text style={[styles.bannerLabel, { color: tone.fg }]}>VERDICT</Text>
        <Text style={[styles.bannerTitle, { color: tone.fg }]}>
          {result.alert || result.source_label || 'Result'}
        </Text>
        <View style={styles.bannerMeta}>
          <Text style={[styles.bannerScore, { color: tone.fg }]}>{sourcePct}%</Text>
          <Text style={[styles.bannerScoreLabel, { color: tone.fg }]}>trust score</Text>
        </View>
      </View>

      {/* Badges */}
      <View style={styles.badges}>
        <Badge label={result.source_label} fg={tier.fg} bg={tier.bg} />
        {result.time_label ? (
          <Badge label={result.time_label} fg={timeBadge.fg} bg={timeBadge.bg} icon="◷" />
        ) : null}
        {result.recirculated ? (
          <Badge label="Republished" fg={colors.warn} bg={colors.warnSoft} icon="↺" />
        ) : null}
        {result.is_known_source === false ? (
          <Badge label="Unverified source" fg={colors.risky} bg={colors.riskySoft} icon="!" />
        ) : null}
        {(result.time_label === 'Old' || result.time_label === 'Very Old') ? (
          <Badge label="Outdated" fg={colors.risky} bg={colors.riskySoft} icon="!" />
        ) : null}
        {result.is_sri_lankan_source ? (
          <Badge label=".lk source" fg={colors.info} bg={colors.infoSoft} />
        ) : null}
        {result.mentions_sri_lanka ? (
          <Badge label="Mentions Sri Lanka" fg={colors.info} bg={colors.infoSoft} />
        ) : null}
        {result.detected_language ? (
          <Badge
            label={LANG_LABEL[result.detected_language] || `Detected: ${result.detected_language}`}
            fg={colors.primary}
            bg={colors.primarySoft}
          />
        ) : null}
      </View>

      {/* Source */}
      <Card>
        <Text style={typography.h3}>Source</Text>
        <View style={{ marginTop: spacing.sm }}>
          {result.publisher ? (
            <Text style={[typography.body, { fontWeight: '700' }]}>{result.publisher}</Text>
          ) : null}
          {result.domain ? (
            <Text style={[typography.small, { marginTop: 2 }]}>{result.domain}</Text>
          ) : null}
          {ageText ? (
            <Text style={[typography.small, { marginTop: spacing.sm }]}>Published {ageText}</Text>
          ) : null}
        </View>
      </Card>

      {/* Reasons */}
      {Array.isArray(result.reasons) && result.reasons.length > 0 ? (
        <Card>
          <Text style={typography.h3}>Why this verdict</Text>
          <View style={{ marginTop: spacing.sm }}>
            {result.reasons.map((r, i) => (
              <View key={i} style={styles.bulletRow}>
                <View style={[styles.bullet, { backgroundColor: tone.fg }]} />
                <Text style={[typography.body, styles.bulletText]}>{r}</Text>
              </View>
            ))}
          </View>
        </Card>
      ) : null}

      {/* Scores */}
      <Card>
        <Text style={typography.h3}>Scores</Text>
        <View style={{ marginTop: spacing.md }}>
          <ScoreBar label="Source credibility" value={result.source_score} color={tone.fg} />
          <ScoreBar label="Temporal freshness" value={result.temporal_score} color={timeBadge.fg} />
          <ScoreBar label="Assessment confidence" value={result.confidence} color={colors.primary} />
        </View>
        <Text style={[typography.tiny, { marginTop: 4 }]}>
          {sourcePct}% trust · {tempPct}% fresh · {confidencePct}% confident
        </Text>
      </Card>

      {/* Breakdown */}
      {result.breakdown && typeof result.breakdown === 'object' ? (
        <Card>
          <Text style={typography.h3}>Feature breakdown</Text>
          <View style={{ marginTop: spacing.md }}>
            {Object.keys(BREAKDOWN_LABELS).map((key) =>
              typeof result.breakdown[key] === 'number' ? (
                <ScoreBar
                  key={key}
                  label={BREAKDOWN_LABELS[key]}
                  value={result.breakdown[key]}
                  color={colors.primary}
                />
              ) : null,
            )}
          </View>
        </Card>
      ) : null}

      {/* Diagnostics (collapsible) */}
      <Card>
        <Pressable onPress={() => setShowDetails((v) => !v)} hitSlop={6}>
          <View style={styles.detailsToggle}>
            <Text style={typography.h3}>Diagnostics</Text>
            <Text style={styles.detailsToggleText}>{showDetails ? 'Hide' : 'Show'}</Text>
          </View>
        </Pressable>
        {showDetails ? (
          <View style={{ marginTop: spacing.md }}>
            <KV k="ML prediction" v={result.ml_prediction === 1 ? '1 (trusted)' : '0 (not trusted)'} />
            <KV k="ML confidence" v={fmt(result.ml_confidence)} />
            <KV k="ML probability trusted" v={fmt(result.ml_probability_trusted)} />
            <KV k="Rule score" v={fmt(result.rule_score)} />
            <KV k="Source tier" v={result.source_tier || '—'} />
            <KV k="Known source" v={boolText(result.is_known_source)} />
            <KV k="Sri Lankan source" v={boolText(result.is_sri_lankan_source)} />
            <KV k="Mentions Sri Lanka" v={boolText(result.mentions_sri_lanka)} />
            <KV k="Recirculated" v={boolText(result.recirculated)} />
            <KV
              k="Age (days)"
              v={typeof result.age_days === 'number' ? result.age_days.toFixed(2) : '—'}
            />
          </View>
        ) : null}
      </Card>
    </View>
  );
}

function KV({ k, v }) {
  return (
    <View style={styles.kvRow}>
      <Text style={styles.kvKey}>{k}</Text>
      <Text style={styles.kvVal}>{v}</Text>
    </View>
  );
}

function toPct(n) {
  if (typeof n !== 'number') return 0;
  return Math.round(Math.max(0, Math.min(1, n)) * 100);
}

function fmt(n) {
  return typeof n === 'number' ? n.toFixed(3) : '—';
}

function boolText(b) {
  if (b === true) return 'Yes';
  if (b === false) return 'No';
  return '—';
}

function formatAge(days) {
  if (typeof days !== 'number' || Number.isNaN(days)) return null;
  if (days < 1) {
    const hours = Math.max(1, Math.round(days * 24));
    return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  }
  if (days < 30) {
    const d = Math.round(days);
    return `${d} day${d === 1 ? '' : 's'} ago`;
  }
  if (days < 365) {
    const m = Math.round(days / 30);
    return `${m} month${m === 1 ? '' : 's'} ago`;
  }
  const y = (days / 365).toFixed(1);
  return `${y} year${y === '1.0' ? '' : 's'} ago`;
}

const styles = StyleSheet.create({
  banner: {
    borderRadius: radius.xl,
    borderWidth: 1,
    padding: spacing.xl,
    marginBottom: spacing.md,
  },
  bannerLabel: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.4,
    opacity: 0.8,
  },
  bannerTitle: {
    fontSize: 24,
    fontWeight: '800',
    marginTop: 6,
  },
  bannerMeta: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginTop: spacing.md,
  },
  bannerScore: {
    fontSize: 38,
    fontWeight: '900',
    letterSpacing: -1,
  },
  bannerScoreLabel: {
    fontSize: 13,
    fontWeight: '700',
    marginLeft: 8,
    textTransform: 'uppercase',
    letterSpacing: 1,
    opacity: 0.85,
  },
  badges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.sm,
  },
  bulletRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  bullet: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginTop: 8,
    marginRight: spacing.md,
  },
  bulletText: { flex: 1 },
  detailsToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  detailsToggleText: { color: colors.primary, fontWeight: '700', fontSize: 13 },
  kvRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  kvKey: { color: colors.textMuted, fontSize: 13 },
  kvVal: { color: colors.text, fontSize: 13, fontWeight: '600', marginLeft: spacing.md },
});
