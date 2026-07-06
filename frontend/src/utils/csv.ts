function escapeCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  const str = typeof value === 'string' ? value : String(value);
  if (/[",\n\r]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function toCsv(rows: Array<Record<string, unknown>>, columns?: string[]): string {
  if (!rows.length) return '';
  const cols = columns ?? Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
  const header = cols.map(escapeCell).join(',');
  const body = rows
    .map((row) => cols.map((c) => escapeCell(row[c])).join(','))
    .join('\n');
  return `${header}\n${body}\n`;
}

export function downloadBlob(content: string, filename: string, mime = 'text/csv'): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8;` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function downloadJson(data: unknown, filename: string): void {
  const content = JSON.stringify(data, null, 2);
  downloadBlob(content, filename, 'application/json');
}
