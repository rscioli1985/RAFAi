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

export type LoginResponse = {
  user_id: string
  email: string
  display_name: string | null
  organizations: { id: string; name: string; slug: string; role_slugs: string[] }[]
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.detail || 'Invalid credentials')
  }
  return res.json()
}

export type Subreddit = {
  id: number
  name: string
  description: string | null
  status: string
  poll_interval_minutes: number
  last_fetched_at: string | null
  last_post_id: string | null
  created_at: string
  updated_at: string
  keywords: number[]
}

export async function getSubreddits(): Promise<Subreddit[]> {
  const res = await fetch(`${API_BASE}/subreddits`)
  if (!res.ok) throw new Error('Failed to load subreddits')
  return res.json()
}

export async function createSubreddit(input: { name: string; description?: string; poll_interval_minutes?: number }) {
  const res = await fetch(`${API_BASE}/subreddits`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.detail || 'Failed to create subreddit')
  }
  return res.json()
}

export async function updateSubreddit(
  id: number,
  input: { description?: string | null; status?: string; poll_interval_minutes?: number; keyword_ids?: number[] },
) {
  const res = await fetch(`${API_BASE}/subreddits/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.detail || 'Failed to update subreddit')
  }
  return res.json()
}

export type Keyword = {
  id: number
  term: string
  description: string | null
  status: string
  created_at: string
  updated_at: string
}

export async function getKeywords(): Promise<Keyword[]> {
  const res = await fetch(`${API_BASE}/keywords`)
  if (!res.ok) throw new Error('Failed to load keywords')
  return res.json()
}

export async function createKeyword(input: { term: string; description?: string }) {
  const res = await fetch(`${API_BASE}/keywords`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.detail || 'Failed to create keyword')
  }
  return res.json()
}

export async function deleteSubreddit(id: number) {
  const res = await fetch(`${API_BASE}/subreddits/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete subreddit')
}
