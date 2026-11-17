import { BookOpen, LoaderCircle, Send, ShieldAlert } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api'
import type { QaResponse } from '../types'

interface Message {
  id: number
  question: string
  response?: QaResponse
  error?: string
}

export function KnowledgePanel() {
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    const text = question.trim()
    if (!text) return
    const id = Date.now()
    setMessages((items) => [...items, { id, question: text }])
    setQuestion('')
    setBusy(true)
    try {
      const response = await api.ask(text)
      setMessages((items) =>
        items.map((item) => (item.id === id ? { ...item, response } : item)),
      )
    } catch (err) {
      setMessages((items) =>
        items.map((item) =>
          item.id === id
            ? { ...item, error: err instanceof Error ? err.message : '问答失败' }
            : item,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="knowledge-panel">
      <div className="knowledge-panel__intro">
        <BookOpen size={25} />
        <div>
          <h2>租房依据问答</h2>
          <p>只回答押金、维修、退租、续租、交接等住宅租赁问题。</p>
        </div>
      </div>
      <div className="knowledge-feed" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty-state">
            <ShieldAlert size={24} />
            <strong>先问一个租房问题</strong>
            <p>例如：“押金退还是否应该写具体天数？”</p>
          </div>
        )}
        {messages.map((message) => (
          <article className="qa-message" key={message.id}>
            <p className="qa-message__question">{message.question}</p>
            {!message.response && !message.error && (
              <div className="qa-message__loading">
                <LoaderCircle size={16} className="spin" />
                正在检索租房知识库
              </div>
            )}
            {message.error && <p className="form-error">{message.error}</p>}
            {message.response && (
              <div className={`qa-answer ${message.response.in_scope ? '' : 'is-out'}`}>
                <p>{message.response.answer}</p>
                {message.response.citations.map((citation) => (
                  <div className="citation-mini" key={`${message.id}-${citation.source_id}`}>
                    <strong>{citation.source_title}</strong>
                    <span>{citation.article}</span>
                    <p>{citation.quote}</p>
                    <small>版本 {citation.effective_date}</small>
                  </div>
                ))}
                <small>{message.response.limitations.join(' · ')}</small>
              </div>
            )}
          </article>
        ))}
      </div>
      <form className="qa-composer" onSubmit={submit}>
        <label htmlFor="rental-question">输入租房问题</label>
        <div>
          <input
            id="rental-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="例如：提前退租违约金应该怎么约定？"
          />
          <button className="btn btn--primary" type="submit" disabled={busy || !question.trim()}>
            <Send size={17} />
            检索依据
          </button>
        </div>
      </form>
    </div>
  )
}
