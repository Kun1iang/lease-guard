export interface User {
  id: number
  username: string
  role: string
  review_quota: number
  question_quota: number
  reviews_used: number
  questions_used: number
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface DocumentInfo {
  id: string
  filename: string
  mime_type: string
  parse_status: string
  page_count: number
  ocr_used: boolean
  created_at: string
}

export interface Review {
  id: string
  document_id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  stage: string
  progress: number
  summary: string
  error_code: string | null
  created_at: string
}

export interface Evidence {
  page_no: number
  quote: string
  kind: 'exact' | 'absence'
  verified: boolean
}

export interface Citation {
  source_id: string
  source_title: string
  article: string
  effective_date: string
  quote: string
  official_url: string
}

export interface Finding {
  id: string
  rule_id: string
  category: string
  title: string
  severity: 'high' | 'medium' | 'low' | 'review'
  status: string
  summary: string
  impact: string
  suggestion: string
  legal_basis: Citation[]
  user_action: string | null
  evidence: Evidence[]
}

export interface PageText {
  page_no: number
  text: string
}

export interface Report {
  review: Review
  document: DocumentInfo
  pages: PageText[]
  findings: Finding[]
  notice: string
}

export interface QaResponse {
  in_scope: boolean
  answer: string
  citations: Citation[]
  limitations: string[]
}
