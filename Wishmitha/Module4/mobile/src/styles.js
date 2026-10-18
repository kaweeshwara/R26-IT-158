import {StyleSheet} from 'react-native';

export const colors = {
  background: '#f4f7fb',
  surface: '#ffffff',
  ink: '#172b4d',
  muted: '#53657d',
  accent: '#135d9e',
  border: '#d4deea',
  warning: '#fff3d6',
  danger: '#9f3131',
  success: '#176b46',
};

export const styles = StyleSheet.create({
  page: {flexGrow: 1, padding: 18, paddingBottom: 36},
  title: {color: colors.ink, fontSize: 26, fontWeight: '700', marginBottom: 8},
  subtitle: {color: colors.muted, fontSize: 15, lineHeight: 22, marginBottom: 18},
  card: {
    backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 14,
    borderWidth: 1, marginBottom: 14, padding: 16,
  },
  label: {color: colors.ink, fontSize: 15, fontWeight: '600', marginBottom: 7, marginTop: 12},
  input: {
    backgroundColor: colors.surface, borderColor: colors.border, borderRadius: 10,
    borderWidth: 1, color: colors.ink, fontSize: 16, minHeight: 46, padding: 12,
  },
  multiline: {minHeight: 150, textAlignVertical: 'top'},
  button: {
    alignItems: 'center', backgroundColor: colors.accent, borderRadius: 10,
    justifyContent: 'center', marginTop: 16, minHeight: 48, paddingHorizontal: 14,
  },
  buttonText: {color: '#fff', fontSize: 16, fontWeight: '700'},
  secondaryButton: {backgroundColor: '#e7eef7'},
  secondaryButtonText: {color: colors.ink},
  error: {color: colors.danger, fontSize: 14, lineHeight: 20, marginTop: 12},
  small: {color: colors.muted, fontSize: 13, lineHeight: 19},
  heading: {color: colors.ink, fontSize: 18, fontWeight: '700', marginBottom: 8},
  row: {alignItems: 'center', flexDirection: 'row', gap: 10},
  score: {color: colors.ink, fontSize: 42, fontWeight: '800'},
  verdict: {fontSize: 18, fontWeight: '800', marginTop: 4},
});
