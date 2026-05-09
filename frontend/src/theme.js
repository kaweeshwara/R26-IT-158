export const colors = {
  bg: '#f6f7fb',
  card: '#ffffff',
  cardAlt: '#f1f3f9',
  border: '#e3e6ee',
  text: '#0f172a',
  textMuted: '#475569',
  textFaint: '#64748b',

  primary: '#4f46e5',
  primaryDark: '#3730a3',
  primarySoft: '#eef2ff',

  trusted: '#16a34a',
  trustedSoft: '#dcfce7',
  moderate: '#d97706',
  moderateSoft: '#fef3c7',
  risky: '#dc2626',
  riskySoft: '#fee2e2',

  info: '#0284c7',
  infoSoft: '#e0f2fe',
  warn: '#b45309',
  warnSoft: '#fef3c7',
  neutral: '#475569',
  neutralSoft: '#e2e8f0',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
};

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 22,
  pill: 999,
};

export const typography = {
  h1: { fontSize: 26, fontWeight: '800', color: colors.text },
  h2: { fontSize: 20, fontWeight: '700', color: colors.text },
  h3: { fontSize: 16, fontWeight: '700', color: colors.text },
  body: { fontSize: 15, color: colors.text },
  small: { fontSize: 13, color: colors.textMuted },
  tiny: { fontSize: 11, color: colors.textFaint, letterSpacing: 0.5 },
};

export function tierTone(label) {
  const v = (label || '').toLowerCase();
  if (v === 'trusted') return { fg: colors.trusted, bg: colors.trustedSoft };
  if (v === 'moderate') return { fg: colors.moderate, bg: colors.moderateSoft };
  if (v === 'risky' || v === 'blacklisted') return { fg: colors.risky, bg: colors.riskySoft };
  return { fg: colors.neutral, bg: colors.neutralSoft };
}

export function timeTone(label) {
  const v = (label || '').toLowerCase();
  if (v === 'fresh') return { fg: colors.trusted, bg: colors.trustedSoft };
  if (v === 'recent') return { fg: colors.info, bg: colors.infoSoft };
  if (v === 'old') return { fg: colors.warn, bg: colors.warnSoft };
  if (v === 'very old') return { fg: colors.risky, bg: colors.riskySoft };
  return { fg: colors.neutral, bg: colors.neutralSoft };
}

export function alertTone(label, sourceScore) {
  if (typeof sourceScore === 'number') {
    if (sourceScore >= 0.7) return { fg: colors.trusted, bg: colors.trustedSoft };
    if (sourceScore >= 0.4) return { fg: colors.moderate, bg: colors.moderateSoft };
    return { fg: colors.risky, bg: colors.riskySoft };
  }
  return tierTone(label);
}
