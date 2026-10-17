export function currentMonth() {
  return new Date().toISOString().slice(0, 7);
}

export function formatDate(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(`${value}T00:00:00`));
}

export function formatDateTime(value) {
  if (!value) return '—';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

export function monthLabel(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }).format(new Date(`${value}-01T00:00:00`));
}

export function displayError(error, fallback = 'Something went wrong. Please try again.') {
  return error?.message || fallback;
}
