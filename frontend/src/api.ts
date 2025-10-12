export type Health = { status: string; db: string; version: string }

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}

export type Message = { role: 'user' | 'assistant'; content: string }

export async function mockChat(query: string): Promise<Message> {
  // Demo mode: simple echo with canned citation note
  await new Promise(r => setTimeout(r, 400))
  return {
    role: 'assistant',
    content: `Demo reply for: "${query}"\n\n(Citations will appear here when backend is connected.)`,
  }
}

export async function chatStream(
  query: string,
  onToken: (t: string) => void,
): Promise<void> {
  const url = `${API_BASE}/v1/chat/stream`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!res.ok || !res.body) throw new Error(`Chat stream failed: ${res.status}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const parts = buf.split('\n\n')
    buf = parts.pop() || ''
    for (const evt of parts) {
      if (!evt.startsWith('data:')) continue
      const data = evt.slice(5).trim()
      try {
        const json = JSON.parse(data)
        if (json.done) return
        if (json.delta) onToken(json.delta + ' ')
      } catch (_) {
        // ignore parse errors
      }
    }
  }
}
