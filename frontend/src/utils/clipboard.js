export async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const input = window.document.createElement('textarea')
  input.value = text
  input.setAttribute('readonly', '')
  input.style.position = 'fixed'
  input.style.opacity = '0'
  window.document.body.appendChild(input)
  input.select()
  const copied = window.document.execCommand('copy')
  input.remove()
  if (!copied) throw new Error('Clipboard is unavailable')
}
