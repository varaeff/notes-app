export function secondsUntil(expiresAt) {
  if (!expiresAt) return 0;
  return Math.max(0, Math.ceil((new Date(expiresAt).getTime() - Date.now()) / 1000));
}

export function formatRemaining(seconds) {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}:${String(rest).padStart(2, '0')}`;
}

export function getBotUrl(botUsername) {
  return `https://t.me/${botUsername}`;
}

export const TELEGRAM_TIMEZONE_OPTIONS = [
  'UTC',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Moscow',
  'Asia/Tbilisi',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Bangkok',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Australia/Sydney',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Sao_Paulo',
];

export function getBrowserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || null;
  } catch {
    return null;
  }
}

export function getTimezoneOptions(...extraTimezones) {
  return Array.from(
    new Set([
      ...extraTimezones.filter(Boolean),
      ...TELEGRAM_TIMEZONE_OPTIONS,
    ])
  );
}
