import { useEffect, useState } from 'react'
import { LoaderCircle } from 'lucide-react'
import { api, getToken, setToken } from './api'
import { Landing } from './components/Landing'
import { Workspace } from './components/Workspace'
import type { AuthResponse, User } from './types'

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(() => Boolean(getToken()))

  useEffect(() => {
    if (!getToken()) return
    api.me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setChecking(false))
  }, [])

  function acceptAuth(result: AuthResponse) {
    setToken(result.access_token)
    setUser(result.user)
  }

  if (checking) {
    return (
      <div className="boot-screen">
        <LoaderCircle className="spin" size={24} />
        <span>正在打开租约守护</span>
      </div>
    )
  }

  if (user) {
    return (
      <Workspace
        user={user}
        onLogout={() => {
          setToken(null)
          setUser(null)
        }}
      />
    )
  }

  return (
    <Landing
      onTrial={async () => acceptAuth(await api.trial())}
      onLogin={async (username, password) => acceptAuth(await api.login(username, password))}
      onRegister={async (username, password) => acceptAuth(await api.register(username, password))}
    />
  )
}

export default App
