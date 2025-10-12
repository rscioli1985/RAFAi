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

