/** Client-side mirror of ``core/password_policy.py``. Keep in sync. */

export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_LENGTH = 128;

const COMMON_PASSWORDS = new Set([
  "password",
  "password1",
  "passw0rd",
  "12345678",
  "123456789",
  "1234567890",
  "qwerty123",
  "qwertyuiop",
  "letmein1",
  "welcome1",
  "admin1234",
  "iloveyou1",
  "abc12345",
  "changeme1",
  "streamclip",
  "qclip1234",
]);

export function validatePassword(password: string): string | null {
  if (!password) return "Password is required.";
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  if (password.length > MAX_PASSWORD_LENGTH) {
    return `Password must be at most ${MAX_PASSWORD_LENGTH} characters.`;
  }
  const hasLetter = /[A-Za-z]/.test(password);
  const hasNonLetter = /[^A-Za-z]/.test(password);
  if (!(hasLetter && hasNonLetter)) {
    return "Password must include letters and at least one number or symbol.";
  }
  if (COMMON_PASSWORDS.has(password.toLowerCase())) {
    return "That password is too common. Pick something harder to guess.";
  }
  return null;
}
