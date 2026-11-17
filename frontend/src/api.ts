import type {
  AuthResponse,
  DocumentInfo,
  QaResponse,
  Report,
  Review,
  User,
} from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? ''
const TOKEN_KEY = 'lease-guard-token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${API_BASE}/api${path}`, { ...init, headers })
  if (!response.ok) {
    let message = `请求失败 (${response.status})`
    try {
      const payload = await response.json()
      if (typeof payload.detail === 'string') {
        message = payload.detail === 'OUT_OF_SCOPE'
          ? '本服务只回答中国大陆住宅租赁问题。'
          : payload.detail
      }
    } catch {
      message = `${message}`
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export const api = {
  trial: () => request<AuthResponse>('/auth/trial', { method: 'POST' }),
  login: (username: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  register: (username: string, password: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<User>('/auth/me'),
  sampleReview: () => request<Review>('/reviews/sample', { method: 'POST' }),
  upload: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<DocumentInfo>('/documents/upload', { method: 'POST', body })
  },
  submitText: (title: string, text: string) =>
    request<DocumentInfo>('/documents/text', {
      method: 'POST',
      body: JSON.stringify({ title, text }),
    }),
  startReview: (documentId: string, city = '') =>
    request<Review>('/reviews', {
      method: 'POST',
      body: JSON.stringify({ document_id: documentId, city }),
    }),
  listReviews: () => request<Review[]>('/reviews'),
  getReview: (reviewId: string) => request<Review>(`/reviews/${reviewId}`),
  getReport: (reviewId: string) => request<Report>(`/reviews/${reviewId}/report`),
  updateFinding: (findingId: string, action: 'confirm' | 'ignore' | 'false_positive') =>
    request<{ ok: boolean }>(`/findings/${findingId}/action?action=${action}`, {
      method: 'PATCH',
    }),
  ask: (question: string, city = '') =>
    request<QaResponse>('/rental-qa', {
      method: 'POST',
      body: JSON.stringify({ question, city }),
    }),
}

export async function pollReview(
  reviewId: string,
  onUpdate: (review: Review) => void,
  interval = 700,
): Promise<Review> {
  for (;;) {
    const review = await api.getReview(reviewId)
    onUpdate(review)
    if (review.status === 'succeeded' || review.status === 'failed') return review
    await new Promise((resolve) => window.setTimeout(resolve, interval))
  }
}
