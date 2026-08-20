import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useConflictAwareSave } from './useConflictAwareSave.js'

const options = (apiSave, onSaved = vi.fn()) => ({
  apiSave, onSaved,
  extractComparable: (resource) => resource.metadata,
  extractRevision: (resource) => resource.revision,
})

describe('useConflictAwareSave', () => {
  it('reports successful saves', async () => {
    const saved = { revision: 2, metadata: { name: 'Mine' } }
    const apiSave = vi.fn().mockResolvedValue(saved)
    const onSaved = vi.fn()
    const { result } = renderHook(() => useConflictAwareSave(options(apiSave, onSaved)))
    await act(() => result.current.attempt({ name: 'Mine' }, { name: 'Base' }, 1))
    expect(apiSave).toHaveBeenCalledWith({ name: 'Mine' }, 1)
    expect(onSaved).toHaveBeenCalledWith(saved)
  })

  it('automatically retries non-conflicting stale writes', async () => {
    const stale = { status: 412, body: { detail: {
      current: { revision: 2, metadata: { name: 'Base', description: 'Remote' } },
    } } }
    const apiSave = vi.fn()
      .mockRejectedValueOnce(stale)
      .mockResolvedValueOnce({ revision: 3, metadata: { name: 'Mine', description: 'Remote' } })
    const { result } = renderHook(() => useConflictAwareSave(options(apiSave)))
    await act(() => result.current.attempt(
      { name: 'Mine', description: 'Old' }, { name: 'Base', description: 'Old' }, 1,
    ))
    expect(apiSave).toHaveBeenNthCalledWith(2, { name: 'Mine', description: 'Remote' }, 2)
    expect(result.current.conflict).toBeNull()
  })

  it('exposes true conflicts for resolution and supports cancellation', async () => {
    const apiSave = vi.fn().mockRejectedValue({ status: 412, body: { detail: {
      current: { revision: 2, metadata: { name: 'Theirs' } },
    } } })
    const { result } = renderHook(() => useConflictAwareSave(options(apiSave)))
    await act(() => result.current.attempt({ name: 'Mine' }, { name: 'Base' }, 1))
    await waitFor(() => expect(result.current.conflict.conflicts.name).toBeDefined())
    act(() => result.current.cancel())
    expect(result.current.conflict).toBeNull()
  })

  it('rethrows ordinary API failures', async () => {
    const error = new Error('offline')
    const { result } = renderHook(() => useConflictAwareSave(options(vi.fn().mockRejectedValue(error))))
    await expect(result.current.attempt({}, {}, 1)).rejects.toBe(error)
  })
})
