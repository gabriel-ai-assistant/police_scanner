/**
 * Safe date formatting utilities.
 *
 * Provides defensive date parsing and formatting to handle:
 * - Null/undefined values
 * - Invalid date strings
 * - Malformed timestamps
 * - Timezone handling via browser locale
 */

/**
 * Format a date value as a full date and time string.
 *
 * @param dateValue - ISO 8601 date string, timestamp, or null/undefined
 * @returns Formatted date string or fallback message
 *
 * @example
 * formatDate("2025-12-12T14:30:00Z") // "12/12/2025, 2:30:00 PM"
 * formatDate(null) // "N/A"
 * formatDate("invalid") // "Invalid Date"
 */
export function formatDate(dateValue: string | null | undefined): string {
  if (!dateValue) return 'N/A';

  try {
    const date = new Date(dateValue);
    // Check if date is valid
    if (isNaN(date.getTime())) {
      console.warn('Invalid date value:', dateValue);
      return 'Invalid Date';
    }
    return date.toLocaleString();
  } catch (error) {
    console.error('Date parsing error:', error, dateValue);
    return 'Invalid Date';
  }
}

/**
 * Format a date value as a time string only (no date).
 *
 * @param dateValue - ISO 8601 date string, timestamp, or null/undefined
 * @returns Formatted time string or fallback message
 *
 * @example
 * formatTime("2025-12-12T14:30:00Z") // "2:30:00 PM"
 * formatTime(null) // "N/A"
 * formatTime("invalid") // "Invalid Time"
 */
export function formatTime(dateValue: string | null | undefined): string {
  if (!dateValue) return 'N/A';

  try {
    const date = new Date(dateValue);
    if (isNaN(date.getTime())) {
      console.warn('Invalid time value:', dateValue);
      return 'Invalid Time';
    }
    return date.toLocaleTimeString();
  } catch (error) {
    console.error('Time parsing error:', error, dateValue);
    return 'Invalid Time';
  }
}

/**
 * Format a date value as a short date string (no time).
 *
 * @param dateValue - ISO 8601 date string, timestamp, or null/undefined
 * @returns Formatted date string or fallback message
 *
 * @example
 * formatDateOnly("2025-12-12T14:30:00Z") // "12/12/2025"
 * formatDateOnly(null) // "N/A"
 */
export function formatDateOnly(dateValue: string | null | undefined): string {
  if (!dateValue) return 'N/A';

  try {
    const date = new Date(dateValue);
    if (isNaN(date.getTime())) {
      console.warn('Invalid date value:', dateValue);
      return 'Invalid Date';
    }
    return date.toLocaleDateString();
  } catch (error) {
    console.error('Date parsing error:', error, dateValue);
    return 'Invalid Date';
  }
}

/**
 * Check if a date value is valid.
 *
 * @param dateValue - Any date value to validate
 * @returns true if the date is valid, false otherwise
 */
export function isValidDate(dateValue: any): boolean {
  if (!dateValue) return false;

  try {
    const date = new Date(dateValue);
    return !isNaN(date.getTime());
  } catch {
    return false;
  }
}
