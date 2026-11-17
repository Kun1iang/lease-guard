import {
  AlertTriangle,
  BookOpenCheck,
  Check,
  ChevronRight,
  CircleAlert,
  FileText,
  MessageSquareText,
  Quote,
  ShieldCheck,
  X,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { api } from '../api'
import type { Finding, PageText, Report } from '../types'
import { KnowledgePanel } from './KnowledgePanel'

interface ReviewWorkspaceProps {
  report: Report
  onReportChange: (report: Report) => void
}

const severityLabel = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
  review: '待核实',
}

function HighlightedPage({ page, finding }: { page: PageText; finding?: Finding }) {
  const quote = finding?.evidence[0]?.quote
  if (!quote || finding?.evidence[0]?.kind === 'absence') {
    return <div className="contract-page__text">{page.text}</div>
  }
  const position = page.text.indexOf(quote)
  if (position === -1) {
    return <div className="contract-page__text">{page.text}</div>
  }
  return (
    <div className="contract-page__text">
      {page.text.slice(0, position)}
      <mark>{quote}</mark>
      {page.text.slice(position + quote.length)}
    </div>
  )
}

export function ReviewWorkspace({ report, onReportChange }: ReviewWorkspaceProps) {
  const [tab, setTab] = useState<'findings' | 'qa' | 'report'>('findings')
  const [filter, setFilter] = useState<'all' | 'high' | 'medium' | 'review'>('all')
  const [selectedId, setSelectedId] = useState(report.findings[0]?.id ?? '')
  const [pageNo, setPageNo] = useState(report.findings[0]?.evidence[0]?.page_no ?? 1)

  const selected = report.findings.find((item) => item.id === selectedId)
  const page = report.pages.find((item) => item.page_no === pageNo) ?? report.pages[0]
  const filtered = useMemo(
    () =>
      report.findings.filter((finding) => {
        if (filter === 'all') return true
        if (filter === 'review') return finding.status === 'needs_review'
        return finding.severity === filter
      }),
    [filter, report.findings],
  )
  const counts = useMemo(
    () => ({
      high: report.findings.filter((item) => item.severity === 'high').length,
      medium: report.findings.filter((item) => item.severity === 'medium').length,
      review: report.findings.filter((item) => item.status === 'needs_review').length,
    }),
    [report.findings],
  )

  function selectFinding(finding: Finding) {
    setSelectedId(finding.id)
    setPageNo(finding.evidence[0]?.page_no ?? 1)
  }

  async function updateAction(finding: Finding, action: 'confirm' | 'ignore' | 'false_positive') {
    await api.updateFinding(finding.id, action)
    onReportChange({
      ...report,
      findings: report.findings.map((item) =>
        item.id === finding.id ? { ...item, user_action: action } : item,
      ),
    })
  }

  return (
    <div className="review-shell">
      <div className="review-toolbar">
        <div>
          <span className="review-toolbar__file"><FileText size={16} />{report.document.filename}</span>
          <span>{report.document.page_count} 页</span>
          {report.document.ocr_used && <span>包含 OCR</span>}
        </div>
        <div className="review-toolbar__stats">
          <span className="stat-high">{counts.high} 高风险</span>
          <span>{counts.medium} 中风险</span>
          <span>{counts.review} 待核实</span>
        </div>
      </div>

      <div className="review-grid">
        <section className="document-pane" aria-label="合同原文">
          <div className="document-pane__pages">
            {report.pages.map((item) => (
              <button
                type="button"
                key={item.page_no}
                className={item.page_no === pageNo ? 'is-active' : ''}
                onClick={() => setPageNo(item.page_no)}
              >
                {item.page_no}
              </button>
            ))}
          </div>
          <article className="contract-page">
            <header>
              <span>合同原文</span>
              <strong>第 {page?.page_no ?? 1} 页</strong>
            </header>
            {page && <HighlightedPage page={page} finding={selected} />}
            {selected?.evidence[0]?.kind === 'absence' && (
              <div className="absence-note">
                <CircleAlert size={16} />
                当前规则未在整份合同中找到明确条款，需人工复核。
              </div>
            )}
          </article>
        </section>

        <section className="analysis-pane" aria-label="审阅结果">
          <div className="analysis-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'findings'}
              onClick={() => setTab('findings')}
            >
              <ShieldCheck size={16} />风险 {report.findings.length}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'qa'}
              onClick={() => setTab('qa')}
            >
              <MessageSquareText size={16} />租房问答
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === 'report'}
              onClick={() => setTab('report')}
            >
              <FileText size={16} />网页报告
            </button>
          </div>

          {tab === 'findings' && (
            <div className="findings-pane">
              <div className="finding-summary">
                <p>{report.review.summary}</p>
                <div className="finding-filters">
                  {[
                    ['all', '全部'],
                    ['high', '高风险'],
                    ['medium', '中风险'],
                    ['review', '待核实'],
                  ].map(([value, label]) => (
                    <button
                      type="button"
                      key={value}
                      className={filter === value ? 'is-active' : ''}
                      onClick={() => setFilter(value as typeof filter)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="finding-list">
                {filtered.map((finding) => (
                  <button
                    type="button"
                    className={`finding-card ${selectedId === finding.id ? 'is-active' : ''}`}
                    key={finding.id}
                    onClick={() => selectFinding(finding)}
                  >
                    <span className={`severity severity--${finding.severity}`}>
                      {finding.severity === 'high'
                        ? <AlertTriangle size={13} />
                        : finding.severity === 'medium'
                          ? <CircleAlert size={13} />
                          : <Check size={13} />}
                      {severityLabel[finding.severity]}
                    </span>
                    <strong>{finding.title}</strong>
                    <p>{finding.summary}</p>
                    <span className="finding-card__meta">
                      {finding.evidence[0]?.kind === 'absence'
                        ? '合同中未找到'
                        : `原文 · 第 ${finding.evidence[0]?.page_no} 页`}
                      <ChevronRight size={14} />
                    </span>
                  </button>
                ))}
              </div>
              {selected && (
                <article className="finding-detail">
                  <div className="finding-detail__head">
                    <div>
                      <span className={`severity severity--${selected.severity}`}>
                        {severityLabel[selected.severity]}
                      </span>
                      <h3>{selected.title}</h3>
                    </div>
                    <span className={selected.status === 'confirmed' ? 'verified' : 'needs-review'}>
                      {selected.status === 'confirmed' ? '证据已核验' : '需要人工确认'}
                    </span>
                  </div>
                  <div className="detail-block">
                    <h4>可能影响</h4>
                    <p>{selected.impact}</p>
                  </div>
                  <div className="detail-block">
                    <h4>协商建议</h4>
                    <p>{selected.suggestion}</p>
                  </div>
                  {selected.legal_basis.length > 0 && (
                    <div className="detail-basis">
                      <BookOpenCheck size={17} />
                      <div>
                        <strong>{selected.legal_basis[0].source_title}</strong>
                        <span>{selected.legal_basis[0].article}</span>
                      </div>
                    </div>
                  )}
                  <div className="finding-actions">
                    <button type="button" onClick={() => updateAction(selected, 'confirm')}>
                      <Check size={15} />确认风险
                    </button>
                    <button type="button" onClick={() => updateAction(selected, 'false_positive')}>
                      <X size={15} />标记误报
                    </button>
                  </div>
                </article>
              )}
            </div>
          )}

          {tab === 'qa' && <KnowledgePanel />}

          {tab === 'report' && (
            <div className="report-pane">
              <div className="report-head">
                <span>租约守护审阅报告</span>
                <strong>{report.document.filename}</strong>
              </div>
              <p className="report-summary">{report.review.summary}</p>
              <div className="report-metrics">
                <div><strong>{report.findings.length}</strong><span>风险总数</span></div>
                <div><strong>{counts.high}</strong><span>高风险</span></div>
                <div><strong>{counts.review}</strong><span>待人工核实</span></div>
              </div>
              <div className="report-findings">
                {report.findings.map((finding, index) => (
                  <article key={finding.id}>
                    <span>{String(index + 1).padStart(2, '0')}</span>
                    <div>
                      <strong>{finding.title}</strong>
                      <p>{finding.summary}</p>
                      {finding.evidence[0]?.quote && (
                        <blockquote><Quote size={14} />{finding.evidence[0].quote}</blockquote>
                      )}
                      <small>建议：{finding.suggestion}</small>
                    </div>
                  </article>
                ))}
              </div>
              <p className="report-notice">{report.notice}</p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
