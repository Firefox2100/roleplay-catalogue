import { expect, it } from 'vitest'
import { passwordStrengthError, PASSWORD_MAX_LENGTH } from './passwordStrength.js'
import { resourceToMetadataPayload } from './resourceMetadataPayload.js'

it.each([
  ['Aa1!', 'tooShort'],
  ['A'.repeat(PASSWORD_MAX_LENGTH + 1) + 'a1!', 'tooLong'],
  ['UPPERCASE1!', 'missingLowercase'],
  ['lowercase1!', 'missingUppercase'],
  ['NoDigits!', 'missingDigit'],
  ['NoSpecial1', 'missingSpecial'],
  ['GoodPass1!', null],
])('validates password policy for %s', (password, expected) => {
  expect(passwordStrengthError(password)).toBe(expected)
})

it('maps a resource to its editable metadata contract', () => {
  expect(resourceToMetadataPayload({
    id: 'resource', revision: 3,
    metadata: { name: 'Name', description: 'Description', language: 'en-uk', visibility: 'public' },
  })).toEqual({
    name: 'Name', description: 'Description', language: 'en-uk', visibility: 'public', tags: [],
  })
})
