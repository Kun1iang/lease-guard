import { useState } from 'react'
import { ArrowRight, LoaderCircle } from 'lucide-react'

interface AuthFormProps {
  onLogin: (username: string, password: string) => Promise<void>
  onRegister: (username: string, password: string) => Promise<void>
}

export function AuthForm({ onLogin, onRegister }: AuthFormProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (mode === 'login') await onLogin(username, password)
      else await onRegister(username, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      <div className="auth-form__switch" role="tablist" aria-label="账号操作">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'login'}
          onClick={() => setMode('login')}
        >
          登录
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'register'}
          onClick={() => setMode('register')}
        >
          注册
        </button>
      </div>
      <label>
        <span>用户名</span>
        <input
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          minLength={3}
          required
        />
      </label>
      <label>
        <span>密码</span>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          minLength={8}
          required
        />
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <p className="form-status" role="status" aria-live="polite">
        {busy ? '正在处理账号请求' : ''}
      </p>
      <button className="btn btn--primary auth-form__submit" type="submit" disabled={busy}>
        {busy ? <LoaderCircle className="spin" size={18} /> : <ArrowRight size={18} />}
        {mode === 'login' ? '进入审阅台' : '创建账号'}
      </button>
    </form>
  )
}
