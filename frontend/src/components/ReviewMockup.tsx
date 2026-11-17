import {
  AlertTriangle,
  Check,
  FileText,
  MessageSquareText,
  ScanLine,
  ShieldCheck,
} from 'lucide-react'

const demoFindings = [
  {
    level: '高',
    tone: 'high',
    title: '押金退还期限不明确',
    quote: '甲方应在合理期限内退还押金。',
    page: 4,
  },
  {
    level: '高',
    tone: 'high',
    title: '维修责任全部转移',
    quote: '房屋及室内设施的维修均由乙方自行承担。',
    page: 6,
  },
  {
    level: '中',
    tone: 'medium',
    title: '缺少物品交接清单',
    quote: '合同中未找到明确的房屋和物品交接清单。',
    page: 1,
  },
]

export function ReviewMockup({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`review-mock ${compact ? 'review-mock--compact' : ''}`} role="img" aria-label="租约守护审阅工作台示意">
      <div className="review-mock__rail">
        <div className="review-mock__brand">
          <span className="brand-mark"><ShieldCheck size={17} /></span>
          <span>租约守护</span>
        </div>
        <div className="review-mock__nav is-active"><FileText size={15} />合同审阅</div>
        <div className="review-mock__nav"><MessageSquareText size={15} />租房问答</div>
        <div className="review-mock__file">
          <ScanLine size={15} />
          <div>
            <strong>住宅租赁合同.pdf</strong>
            <span>12 页 · 图像 + 文本</span>
          </div>
        </div>
      </div>
      <div className="review-mock__doc">
        <div className="review-mock__doc-head">
          <span>第 4 页</span>
          <span>原文核验</span>
        </div>
        <div className="mock-page">
          <span className="mock-kicker">第四条 · 押金</span>
          <p>乙方应支付三个月租金作为押金。</p>
          <p className="is-marked">租赁期满后，甲方应在合理期限内退还押金。</p>
          <p>如房屋或物品存在损坏，甲方可从押金中扣除相应费用。</p>
        </div>
      </div>
      <div className="review-mock__findings">
        <div className="review-mock__summary">
          <span>风险摘要</span>
          <strong>3 项需先核对</strong>
        </div>
        {demoFindings.map((item) => (
          <div className="mock-finding" key={item.title}>
            <div className={`mock-finding__level is-${item.tone}`}>
              {item.level === '高' ? <AlertTriangle size={12} /> : <Check size={12} />}
              {item.level}
            </div>
            <strong>{item.title}</strong>
            <p>{item.quote}</p>
            <span>原文 · 第 {item.page} 页</span>
          </div>
        ))}
      </div>
    </div>
  )
}
