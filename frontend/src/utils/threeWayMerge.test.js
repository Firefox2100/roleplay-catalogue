import { describe, expect, it } from 'vitest'
import { threeWayMerge } from './threeWayMerge.js'

describe('threeWayMerge', () => {
  it('automatically combines independent local and remote edits', () => {
    const result = threeWayMerge(
      { name: 'Original', description: 'Old', tags: ['one'] },
      { name: 'Local', description: 'Old', tags: ['one'] },
      { name: 'Original', description: 'Remote', tags: ['one'] },
    )
    expect(result).toEqual({
      merged: { name: 'Local', description: 'Remote', tags: ['one'] }, conflicts: {},
    })
  })

  it('reports divergent edits and defaults the tentative merge to local', () => {
    const result = threeWayMerge({ name: 'Base' }, { name: 'Mine' }, { name: 'Theirs' })
    expect(result.merged.name).toBe('Mine')
    expect(result.conflicts.name).toEqual({ base: 'Base', local: 'Mine', remote: 'Theirs' })
  })

  it('deeply compares arrays and objects rather than their identity', () => {
    expect(threeWayMerge(
      { settings: { enabled: true }, tags: ['a'] },
      { settings: { enabled: true }, tags: ['a'] },
      { settings: { enabled: true }, tags: ['a'] },
    ).conflicts).toEqual({})
  })

  it('merges keyed entries independently and identifies only true conflicts', () => {
    const result = threeWayMerge(
      { entries: [{ uid: 1, text: 'base' }, { uid: 2, text: 'keep' }] },
      { entries: [{ uid: 1, text: 'local' }, { uid: 2, text: 'keep' }, { uid: 3, text: 'new' }] },
      { entries: [{ uid: 1, text: 'remote' }, { uid: 2, text: 'changed' }] },
      { entries: 'uid' },
    )
    expect(result.merged.entries).toEqual([
      { uid: 1, text: 'local' }, { uid: 2, text: 'changed' }, { uid: 3, text: 'new' },
    ])
    expect(result.conflicts.entries.entries['1']).toEqual({
      base: { uid: 1, text: 'base' }, local: { uid: 1, text: 'local' },
      remote: { uid: 1, text: 'remote' },
    })
  })

  it('handles additions and deletions on either side', () => {
    expect(threeWayMerge({ old: 'x' }, {}, { old: 'x', added: 1 })).toEqual({
      merged: { old: undefined, added: 1 }, conflicts: {},
    })
  })
})
