import React, { useEffect, useMemo, useState } from 'react'
import { getHealth, mockChat, chatStream, type Message } from './api'

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
      .catch((_e) => {
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

export default function App() {
  const { status, info } = useHealth()
  const demoMode = status !== 'up'
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  async function onSend(e: React.FormEvent) {
    e.preventDefault()
    const q = input.trim()
    if (!q) return
    setInput('')
    const userMsg: Message = { role: 'user', content: q }
    setMessages((prev) => [...prev, userMsg])
    setSending(true)
    try {
      if (demoMode) {
        const reply = await mockChat(q)
        setMessages((prev) => [...prev, reply])
      } else {
        let acc = ''
        await chatStream(q, (t) => {
          acc += t
          setMessages((prev) => {
            const head = prev.slice(0, -1)
            const last = prev[prev.length - 1]
            // If last is assistant, append; else create new assistant msg
            if (last && last.role === 'assistant') {
              return [...head, { ...last, content: acc }]
            }
            return [...prev, { role: 'assistant', content: acc }]
          })
        })
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err?.message || 'Failed to get response'}` },
      ])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="app">
      <header>
        <h1>NIL RAG Assistant</h1>
        <span className={`status ${status}`}>{info}</span>
      </header>

      <main>
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty">Ask a NIL question to get started.</div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className="role">{m.role === 'user' ? 'You' : 'Assistant'}</div>
              <div className="content">{m.content}</div>
            </div>
          ))}
        </div>

        <form className="composer" onSubmit={onSend}>
          <input
            type="text"
            placeholder={demoMode ? 'Demo mode: backend not connected' : 'Ask about NIL...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={sending}
            autoFocus
          />
          <button type="submit" disabled={sending || !input.trim()}>
            {sending ? 'Sending...' : 'Send'}
          </button>
        </form>
      </main>

      <footer>
        <small>
          This is an MVP UI. When the backend streaming endpoint is ready, we’ll replace demo replies with
          real RAG answers and citations.
        </small>
      </footer>
    </div>
  )
}
