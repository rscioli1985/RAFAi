import React, { useEffect, useState } from 'react'
import {
  getHealth,
  login,
  type LoginResponse,
  getSubreddits,
  createSubreddit,
  updateSubreddit,
  deleteSubreddit,
  type Subreddit,
  getKeywords,
  createKeyword,
  type Keyword,
} from './api'

function useHealth() {
  const [status, setStatus] = useState<'loading' | 'up' | 'down'>('loading')
  const [info, setInfo] = useState<string>('')
  useEffect(() => {
    let mounted = true
    getHealth()
      .then((h) => {
        if (!mounted) return
        setStatus(h.db === 'up' ? 'up' : 'down')
        setInfo(`API ${h.status}, DB ${h.db}, v${h.version}`)
      })
      .catch(() => {
        if (!mounted) return
        setStatus('down')
        setInfo('Backend not reachable; running in Demo Mode')
      })
    return () => {
      mounted = false
    }
  }, [])
  return { status, info }
}

type SplashProps = {
  onLogin: (email: string, password: string) => Promise<void>
  loading: boolean
  error: string | null
}

function Splash({ onLogin, loading, error }: SplashProps) {
  const [email, setEmail] = useState('admin@goanalog.com')
  const [password, setPassword] = useState('password')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await onLogin(email, password)
  }

  return (
    <div className="splash">
      <section className="hero">
        <p className="eyebrow">Retrieval Augmented NIL Intelligence</p>
        <h2>Centralize NIL knowledge for your organization.</h2>
        <p className="lede">
          Connect Reddit ingestion, FAQs, and AI answers inside one workspace. Start with a pilot org and graduate to a
          production-ready stack.
        </p>
      </section>

      <form className="login-card" onSubmit={handleSubmit}>
        <h3>Sign in</h3>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <div className="form-error">{error}</div>}
        <button type="submit" disabled={loading}>
          {loading ? 'Authenticating…' : 'Enter workspace'}
        </button>
      </form>
    </div>
  )
}

function Home({ auth, status, info }: { auth: LoginResponse; status: string; info: string }) {
  return (
    <div className="home">
      <section className="welcome">
        <p className="eyebrow">Welcome back</p>
        <h2>{auth.display_name ?? auth.email}</h2>
        <p className="lede">
          You are connected to {auth.organizations.length || 'no'} organizations. Choose one below to manage ingestion,
          review FAQs, and launch the chat agent.
        </p>
        <div className="status-pill">
          <span className={`dot ${status}`}></span>
          {info}
        </div>
      </section>

      <section className="org-grid">
        {auth.organizations.length === 0 && (
          <div className="org-card empty-card">No organizations linked yet. Seed one to continue.</div>
        )}
        {auth.organizations.map((org) => (
          <article key={org.id} className="org-card">
            <h3>{org.name}</h3>
            <p className="slug">/{org.slug}</p>
            <p className="roles">Roles: {org.role_slugs.join(', ') || 'Member'}</p>
            <button className="primary">Enter Home</button>
          </article>
        ))}
      </section>

      <ManageSubreddits />
    </div>
  )
}

function ManageSubreddits() {
  const [subreddits, setSubreddits] = useState<Subreddit[]>([])
  const [keywords, setKeywords] = useState<Keyword[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', description: '', pollInterval: 1440, keywordIds: [] as number[] })
  const [newKeyword, setNewKeyword] = useState({ term: '', description: '' })

  async function load() {
    try {
      setLoading(true)
      setError(null)
      const [subs, kws] = await Promise.all([getSubreddits(), getKeywords()])
      setSubreddits(subs)
      setKeywords(kws)
    } catch (err: any) {
      setError(err?.message || 'Failed to load subreddits')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) return
    try {
      await createSubreddit({
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        poll_interval_minutes: form.pollInterval,
        keyword_ids: form.keywordIds,
      })
      setForm({ name: '', description: '', pollInterval: 1440, keywordIds: [] })
      await load()
    } catch (err: any) {
      setError(err?.message || 'Failed to add subreddit')
    }
  }

  async function handleAddKeyword(e: React.FormEvent) {
    e.preventDefault()
    if (!newKeyword.term.trim()) return
    try {
      await createKeyword({ term: newKeyword.term.trim(), description: newKeyword.description.trim() || undefined })
      setNewKeyword({ term: '', description: '' })
      const kw = await getKeywords()
      setKeywords(kw)
    } catch (err: any) {
      setError(err?.message || 'Failed to add keyword')
    }
  }

  async function toggleStatus(subreddit: Subreddit) {
    const nextStatus = subreddit.status === 'active' ? 'paused' : 'active'
    await updateSubreddit(subreddit.id, { status: nextStatus })
    await load()
  }

  async function removeSubreddit(subreddit: Subreddit) {
    if (!confirm(`Remove r/${subreddit.name}?`)) return
    await deleteSubreddit(subreddit.id)
    await load()
  }

  async function updateSubredditKeywords(subreddit: Subreddit, keywordId: number, checked: boolean) {
    const next = checked
      ? [...subreddit.keywords, keywordId]
      : subreddit.keywords.filter((id) => id !== keywordId)
    await updateSubreddit(subreddit.id, { keyword_ids: next })
    await load()
  }

  return (
    <section className="manage-card">
      <div className="manage-header">
        <div>
          <p className="eyebrow">Reddit Sources</p>
          <h3>Tracked Subreddits</h3>
        </div>
        {error && <span className="form-error inline">{error}</span>}
      </div>

      <form className="subreddit-form" onSubmit={handleCreate}>
        <label>
          Subreddit
          <input
            type="text"
            placeholder="e.g. NIL"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            required
          />
        </label>
        <label>
          Description
          <input
            type="text"
            placeholder="Optional note"
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
          />
        </label>
        <label>
          Poll Interval (minutes)
          <input
            type="number"
            min={30}
            max={10080}
            value={form.pollInterval}
            onChange={(e) => setForm((prev) => ({ ...prev, pollInterval: Number(e.target.value) }))}
          />
        </label>
        <label>
          Keywords
          <select
            multiple
            value={form.keywordIds.map(String)}
            onChange={(e) => {
              const selected = Array.from(e.target.selectedOptions).map((opt) => Number(opt.value))
              setForm((prev) => ({ ...prev, keywordIds: selected }))
            }}
          >
            {keywords.map((kw) => (
              <option key={kw.id} value={kw.id}>
                {kw.term}
              </option>
            ))}
          </select>
        </label>
        <button type="submit">Add subreddit</button>
      </form>

      <form className="keyword-form" onSubmit={handleAddKeyword}>
        <input
          type="text"
          placeholder="New keyword"
          value={newKeyword.term}
          onChange={(e) => setNewKeyword((prev) => ({ ...prev, term: e.target.value }))}
        />
        <input
          type="text"
          placeholder="Description"
          value={newKeyword.description}
          onChange={(e) => setNewKeyword((prev) => ({ ...prev, description: e.target.value }))}
        />
        <button type="submit">Save keyword</button>
      </form>

      <div className="subreddit-list">
        {loading && <div className="empty-card">Loading…</div>}
        {!loading && subreddits.length === 0 && <div className="empty-card">No subreddits tracked yet.</div>}
        {!loading &&
          subreddits.map((sub) => (
            <article key={sub.id} className="subreddit-item">
              <div>
                <h4>r/{sub.name}</h4>
                <p>{sub.description || 'No description yet'}</p>
                <small>
                  Interval: {sub.poll_interval_minutes} min · Status: {sub.status}
                  {sub.last_fetched_at && ` · Last ingest ${new Date(sub.last_fetched_at).toLocaleString()}`}
                </small>
                <div className="keyword-tags">
                  {sub.keywords.length === 0 && <span className="tag muted">No keywords</span>}
                  {keywords
                    .filter((kw) => sub.keywords.includes(kw.id))
                    .map((kw) => (
                      <span key={kw.id} className="tag">
                        {kw.term}
                      </span>
                    ))}
                </div>
                <div className="keyword-checklist">
                  {keywords.map((kw) => (
                    <label key={kw.id}>
                      <input
                        type="checkbox"
                        checked={sub.keywords.includes(kw.id)}
                        onChange={(e) => updateSubredditKeywords(sub, kw.id, e.target.checked)}
                      />
                      {kw.term}
                    </label>
                  ))}
                </div>
              </div>
              <div className="subreddit-actions">
                <button type="button" onClick={() => toggleStatus(sub)}>
                  {sub.status === 'active' ? 'Pause' : 'Resume'}
                </button>
                <button type="button" className="danger" onClick={() => removeSubreddit(sub)}>
                  Remove
                </button>
              </div>
            </article>
          ))}
      </div>
    </section>
  )
}

export default function App() {
  const { status, info } = useHealth()
  const [auth, setAuth] = useState<LoginResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleLogin(email: string, password: string) {
    try {
      setLoading(true)
      setError(null)
      const response = await login(email, password)
      setAuth(response)
    } catch (err: any) {
      setError(err?.message || 'Unable to login')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>NIL RAG Pilot</h1>
        <span className={`status ${status}`}>{info}</span>
      </header>

      <main>{auth ? <Home auth={auth} status={status} info={info} /> : <Splash onLogin={handleLogin} loading={loading} error={error} />}</main>

      <footer>
        <small>Next up: connect ingestion runs, FAQ review, and the streaming agent.</small>
      </footer>
    </div>
  )
}
