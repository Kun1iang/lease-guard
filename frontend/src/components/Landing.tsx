import {
  ArrowDown,
  ArrowRight,
  BookOpenCheck,
  Check,
  FileSearch,
  Fingerprint,
  LoaderCircle,
  ScanText,
  ShieldCheck,
} from 'lucide-react'
import { useState } from 'react'
import { AuthForm } from './AuthForm'
import { ReviewMockup } from './ReviewMockup'

interface LandingProps {
  onTrial: () => Promise<void>
  onLogin: (username: string, password: string) => Promise<void>
  onRegister: (username: string, password: string) => Promise<void>
}

export function Landing({ onTrial, onLogin, onRegister }: LandingProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function startTrial() {
    setError('')
    setBusy(true)
    try {
      await onTrial()
    } catch (err) {
      setError(err instanceof Error ? err.message : '无法启动试用')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <header className="nav">
        <div className="wrap nav__bar">
          <a className="skip-link" href="#top">跳到主要内容</a>
          <a className="nav__logo" href="#top">
            <span className="brand-mark"><ShieldCheck size={18} /></span>
            租约守护
          </a>
          <nav className="nav__links" aria-label="主导航">
            <a className="nav__link" href="#workbench">审阅台</a>
            <a className="nav__link" href="#evidence">证据链</a>
            <a className="nav__link" href="#knowledge">租房依据</a>
          </nav>
          <div className="nav__actions">
            <a className="nav__link" href="#account">登录</a>
            <button className="btn btn--primary" type="button" onClick={startTrial} disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={17} /> : null}
              启动试用
            </button>
          </div>
        </div>
      </header>

      <main id="top">
        <section className="hero hero--collage" data-enter aria-labelledby="hero-title">
          <div className="wrap">
            <div className="hero-text hero-split">
              <div className="hero-copy span-5">
              <p className="hero-notice">4 种输入 · 只处理中国大陆住宅租赁</p>
              <h1 id="hero-title">租房合同风险审阅，给第一次签约的租客</h1>
              <p className="t-lead hero__lead">
                上传照片、PDF 或合同文本，逐条查看押金、维修和退租风险。每个结论保留原文、页码和租赁依据。
              </p>
              <div className="btn-row">
                <button className="btn btn--primary" type="button" onClick={startTrial} disabled={busy}>
                  启动试用
                  <ArrowRight className="m-arrow" size={17} />
                </button>
                <a className="btn btn--secondary" href="#account">登录账号</a>
              </div>
              {error && <p className="form-error" role="alert">{error}</p>}
              <dl className="hero-facts">
                <div><dt>输入</dt><dd>照片与文本</dd></div>
                <div><dt>证据</dt><dd>原文与页码</dd></div>
                <div><dt>边界</dt><dd>仅住宅租赁</dd></div>
              </dl>
            </div>
              <div className="hero-visual span-6 start-7">
                <ReviewMockup />
              </div>
            </div>
          </div>
        </section>

        <section className="section section--workbench" id="workbench">
          <div className="wrap">
            <div className="section-head split-head">
              <div>
                <p className="eyebrow">审阅工作台</p>
                <h2>风险、原文、依据放在同一张屏幕上</h2>
              </div>
              <p>
                不是一次性的聊天回答。每条风险都有独立状态，用户可以确认、忽略或标记误报。
              </p>
            </div>
            <div className="workbench-stage">
              <ReviewMockup compact />
            </div>
          </div>
        </section>

        <section className="section" id="evidence">
          <div className="wrap">
            <div className="evidence-top">
              <div className="section-head">
                <p className="eyebrow">证据链</p>
                <h2>让结论可以被复核</h2>
                <p>规则负责发现，模型负责解释，代码再检查引用是否真的存在于合同页。</p>
              </div>
              <div className="visual-mock evidence-visual" role="img" aria-label="风险原文与依据核验流程">
                <img src="/risk-flow.svg" alt="规则命中、原文核验和报告输出的流程" />
              </div>
            </div>
            <div className="feature-grid">
              <article className="feature-card">
                <ScanText size={24} />
                <h3>统一解析合同页</h3>
                <p>PDF、DOCX、照片和粘贴文本都会进入同一套页级数据结构，并保留 OCR 置信度。</p>
              </article>
              <article className="feature-card">
                <FileSearch size={24} />
                <h3>先跑确定性规则</h3>
                <p>押金期限、维修责任、提前解约、入户程序等问题先由可重复检查发现。</p>
              </article>
              <article className="feature-card">
                <Fingerprint size={24} />
                <h3>核验原文证据</h3>
                <p>引用必须能在对应页码找到；缺失条款则会明确标成“未检索到”，不伪造原文。</p>
              </article>
            </div>
          </div>
        </section>

        <section className="section section--ground" id="knowledge">
          <div className="wrap">
            <div className="know-grid">
              <div>
                <p className="eyebrow">租房知识库</p>
                <h2>法律依据只谈租房</h2>
                <p className="know-lead">
                  问答范围限定在房屋、押金、维修、续租、退租和交接。每个回答显示来源、条款、版本和适用范围。
                </p>
                <ul className="check-list">
                  <li><Check size={17} />非租房问题直接拒绝，不扩展成通用法律助手</li>
                  <li><Check size={17} />官方依据和团队风险说明分开标注</li>
                  <li><Check size={17} />知识不足时回答“当前无法确认”</li>
                </ul>
              </div>
              <div className="visual-mock citation-panel">
                <BookOpenCheck size={24} />
                <span className="citation-panel__label">依据卡片</span>
                <strong>住宅租赁合同的主要内容</strong>
                <p>租金、押金、维修、解除和续租应尽量写明。</p>
                <div className="citation-panel__source">
                  <span>中华人民共和国民法典</span>
                  <span>合同编 · 租赁合同章</span>
                </div>
                <img className="citation-panel__visual" src="/legal-flow.svg" alt="租房问题经过范围守卫和依据检索生成带引用回答" />
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="closing" id="account">
        <div className="wrap">
          <div className="footer-shell">
            <div className="closing__grid">
            <div className="closing__copy">
              <p className="eyebrow">试用账号</p>
              <h2>用样例合同走完一次审阅</h2>
              <p>试用账号会加载脱敏样例合同，不消耗正式审阅额度。</p>
              <a className="back-link" href="#top"><ArrowDown size={16} />回到顶部</a>
            </div>
            <div className="account-card">
              <AuthForm onLogin={onLogin} onRegister={onRegister} />
              <div className="trial-note">
                <span>不想注册？</span>
                <button type="button" onClick={startTrial}>直接进入试用</button>
              </div>
            </div>
            </div>
            <div className="legal-row">
              <span>租约守护 · 2026</span>
              <span>合同风险预筛，不构成正式法律意见</span>
            </div>
          </div>
        </div>
      </footer>
    </>
  )
}
