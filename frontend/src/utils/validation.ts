export function isPositiveInt(value: unknown, min = 1, max = 365): boolean {
  if (typeof value !== 'number' || !Number.isInteger(value)) return false;
  return value >= min && value <= max;
}

export function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

export function isValidHorizon(value: number | ''): value is number {
  return typeof value === 'number' && isPositiveInt(value, 1, 365);
}
