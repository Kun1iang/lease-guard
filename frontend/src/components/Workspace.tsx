import {
  ArrowLeft,
  BookOpen,
  ChevronRight,
  CircleUserRound,
  FilePlus2,
  FileScan,
  LoaderCircle,
  LogOut,
  MessageSquareText,
  ShieldCheck,
  Upload,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, pollReview } from '../api'
import type { Report, Review, User } from '../types'
import { KnowledgePanel } from './KnowledgePanel'
import { ReviewWorkspace } from './ReviewWorkspace'

interface WorkspaceProps {
  user: User
  onLogout: () => void
}

type View = 'dashboard' | 'new' | 'review' | 'knowledge'

export function Workspace({ user, onLogout }: WorkspaceProps) {
  const [view, setView] = useState<View>('dashboard')
  const [reviews, setReviews] = useState<Review[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.listReviews().then(setReviews).catch(() => setReviews([]))
  }, [])

  async function refreshReviews() {
    const items = await api.listReviews()
    setReviews(items)
  }

  async function openReview(review: Review) {
    setError('')
    setLoading(review.status === 'succeeded' ? '正在读取审阅报告' : '正在等待审阅完成')
    try {
      const finished = review.status === 'succeeded'
        ? review
        : await pollReview(review.id, (update) => {
            setReviews((items) =>
              items.map((item) => (item.id === update.id ? update : item)),
            )
          })
      if (finished.status === 'failed') throw new Error('审阅任务失败，请重新上传')
      const payload = await api.getReport(finished.id)
      setReport(payload)
      setView('review')
      await refreshReviews()
    } catch (err) {
      setError(err instanceof Error ? err.message : '读取报告失败')
    } finally {
      setLoading('')
    }
  }

  async function startSample() {
    setError('')
    setLoading('正在生成样例审阅')
    try {
      const review = await api.sampleReview()
      await openReview(review)
    } catch (err) {
      setError(err instanceof Error ? err.message : '样例审阅失败')
      setLoading('')
    }
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <button className="app-brand" type="button" onClick={() => setView('dashboard')}>
          <span className="brand-mark"><ShieldCheck size={18} /></span>
          <span>租约守护</span>
        </button>
        <nav aria-label="工作台导航">
          <button
            type="button"
            className={view === 'dashboard' || view === 'review' ? 'is-active' : ''}
            onClick={() => setView('dashboard')}
          >
            <FileScan size={18} />合同审阅
          </button>
          <button type="button" onClick={() => setView('new')}>
            <FilePlus2 size={18} />新建审阅
          </button>
          <button
            type="button"
            className={view === 'knowledge' ? 'is-active' : ''}
            onClick={() => setView('knowledge')}
          >
            <MessageSquareText size={18} />租房问答
          </button>
        </nav>
        <div className="sidebar-account">
          <CircleUserRound size={19} />
          <div>
            <strong>{user.username}</strong>
            <span>{user.role === 'trial' ? '试用账号' : '标准账号'}</span>
          </div>
          <button type="button" aria-label="退出登录" onClick={onLogout}>
            <LogOut size={17} />
          </button>
        </div>
      </aside>

      <main className="app-main">
        <header className="app-topbar">
          <div>
            <span className="app-topbar__context">
              {view === 'review' ? '审阅工作台' : view === 'knowledge' ? '租房知识' : '合同审阅'}
            </span>
            <strong>
              {view === 'review' && report
                ? report.document.filename
                : view === 'knowledge'
                  ? '租房依据问答'
                  : '最近审阅'}
            </strong>
          </div>
          <div className="quota-chip">
            <span>审阅 {Math.max(0, user.review_quota - user.reviews_used)}/{user.review_quota}</span>
            <span>问答 {Math.max(0, user.question_quota - user.questions_used)}/{user.question_quota}</span>
          </div>
        </header>

        {loading && (
          <div className="workspace-loader" role="status">
            <LoaderCircle className="spin" size={24} />
            <strong>{loading}</strong>
            <span>正在解析合同页、执行规则并核验证据</span>
          </div>
        )}
        {error && <div className="workspace-error" role="alert">{error}</div>}

        {!loading && view === 'dashboard' && (
          <Dashboard
            reviews={reviews}
            onNew={() => setView('new')}
            onSample={startSample}
            onOpen={openReview}
          />
        )}
        {!loading && view === 'new' && (
          <NewReview
            onBack={() => setView('dashboard')}
            onCreated={async (review) => {
              await refreshReviews()
              await openReview(review)
            }}
            onError={setError}
          />
        )}
        {!loading && view === 'review' && report && (
          <ReviewWorkspace report={report} onReportChange={setReport} />
        )}
        {!loading && view === 'knowledge' && <KnowledgePanel />}
      </main>
    </div>
  )
}

function Dashboard({
  reviews,
  onNew,
  onSample,
  onOpen,
}: {
  reviews: Review[]
  onNew: () => void
  onSample: () => void
  onOpen: (review: Review) => void
}) {
  return (
    <div className="dashboard">
      <section className="dashboard-hero">
        <div>
          <span className="eyebrow">从合同原文开始</span>
          <h1>上传一份住宅租赁合同</h1>
          <p>照片、PDF、DOCX 或文本都可以。审阅结果会按风险等级排序，并保留原文页码。</p>
          <div className="btn-row">
            <button className="btn btn--primary" type="button" onClick={onNew}>
              <Upload size={17} />上传合同
            </button>
            <button className="btn btn--secondary" type="button" onClick={onSample}>
              查看样例报告
            </button>
          </div>
        </div>
        <div className="dashboard-hero__aside">
          <ShieldCheck size={24} />
          <strong>试用合同不会消耗额度</strong>
          <p>样例使用脱敏住宅租赁合同，可直接体验风险卡片、原文定位和租房问答。</p>
        </div>
      </section>

      <section className="recent-reviews">
        <header>
          <h2>最近审阅</h2>
          <span>{reviews.length} 个任务</span>
        </header>
        {reviews.length === 0 ? (
          <div className="empty-state empty-state--wide">
            <BookOpen size={25} />
            <strong>还没有审阅记录</strong>
            <p>上传合同或先打开样例报告。</p>
          </div>
        ) : (
          <div className="review-list">
            {reviews.map((review) => (
              <button type="button" key={review.id} onClick={() => onOpen(review)}>
                <span className={`review-status is-${review.status}`}>
                  {review.status === 'succeeded' ? '已完成' : review.status === 'failed' ? '失败' : '处理中'}
                </span>
                <div>
                  <strong>租赁合同审阅</strong>
                  <span>{new Date(review.created_at).toLocaleString('zh-CN')}</span>
                </div>
                <p>{review.summary || review.stage}</p>
                <ChevronRight size={18} />
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function NewReview({
  onBack,
  onCreated,
  onError,
}: {
  onBack: () => void
  onCreated: (review: Review) => Promise<void>
  onError: (message: string) => void
}) {
  const [mode, setMode] = useState<'file' | 'text'>('file')
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      const document = mode === 'file'
        ? file
          ? await api.upload(file)
          : null
        : text.trim().length >= 20
          ? await api.submitText('粘贴的租赁合同', text)
          : null
      if (!document) throw new Error(mode === 'file' ? '请选择合同文件' : '请粘贴合同文本')
      const review = await api.startReview(document.id)
      await onCreated(review)
    } catch (err) {
      onError(err instanceof Error ? err.message : '创建审阅失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="new-review">
      <button className="back-button" type="button" onClick={onBack}>
        <ArrowLeft size={16} />返回审阅列表
      </button>
      <div className="new-review__head">
        <span className="eyebrow">新建审阅</span>
        <h1>选择合同输入方式</h1>
        <p>只接受中国大陆住宅租赁合同。上传前请确认文件内容清晰。</p>
      </div>
      <form className="upload-form" onSubmit={submit}>
        <div className="input-switch" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'file'}
            onClick={() => setMode('file')}
          >
            <Upload size={17} />文件与照片
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'text'}
            onClick={() => setMode('text')}
          >
            <FilePlus2 size={17} />粘贴文本
          </button>
        </div>

        {mode === 'file' ? (
          <button className="drop-zone" type="button" onClick={() => inputRef.current?.click()}>
            <Upload size={28} />
            <strong>{file ? file.name : '选择合同文件'}</strong>
            <span>PDF、DOCX、JPG、PNG 或 WEBP，最大 30 MB</span>
            <input
              ref={inputRef}
              type="file"
              hidden
              accept=".pdf,.docx,.jpg,.jpeg,.png,.webp"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </button>
        ) : (
          <label className="text-upload">
            <span>合同正文</span>
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="粘贴住宅租赁合同正文，至少 20 个字符"
              rows={12}
            />
          </label>
        )}
        <div className="upload-form__note">
          <ShieldCheck size={16} />
          <span>原始文件默认保留 24 小时，可随时删除。外部模型调用前会脱敏。</span>
        </div>
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? <LoaderCircle size={17} className="spin" /> : <FileScan size={17} />}
          开始审阅
        </button>
      </form>
    </div>
  )
}
