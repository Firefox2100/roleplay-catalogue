export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_LENGTH = 128

// Mirrors the backend policy in src/roleplay_catalogue/misc/password_strength.py: 8-128
// characters, at least one lowercase letter, one uppercase letter, one number, and one
// character outside A-Za-z0-9. Keep both in sync if the policy ever changes.
const RULES = [
  { key: 'tooShort', test: (password) => password.length >= PASSWORD_MIN_LENGTH },
  { key: 'tooLong', test: (password) => password.length <= PASSWORD_MAX_LENGTH },
  { key: 'missingLowercase', test: (password) => /[a-z]/.test(password) },
  { key: 'missingUppercase', test: (password) => /[A-Z]/.test(password) },
  { key: 'missingDigit', test: (password) => /[0-9]/.test(password) },
  { key: 'missingSpecial', test: (password) => /[^A-Za-z0-9]/.test(password) },
]

// Returns the translation key for the first unmet rule, or null if the password satisfies
// the whole policy. Checked in the same order as the backend so the reported reason matches.
export function passwordStrengthError(password) {
  const failed = RULES.find((rule) => !rule.test(password))
  return failed ? failed.key : null
}
