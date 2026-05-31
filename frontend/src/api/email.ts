import request from './request'

/* ---------- 类型定义 ---------- */
export interface EmailConfigPayload {
  email_address: string
  imap_server: string
  port: number
  password: string
  check_interval_minutes: number
  use_ssl: boolean
}

export interface EmailConfigUpdatePayload {
  email_address?: string
  imap_server?: string
  port?: number
  password?: string
  check_interval_minutes?: number
  use_ssl?: boolean
  is_active?: boolean
}

export interface EmailConfigItem {
  id: number
  email_address: string
  imap_server: string
  port: number
  check_interval_minutes: number
  use_ssl: boolean
  is_active: boolean
  last_check_at: string | null
  created_at: string | null
}

export interface EmailTestPayload {
  email_address: string
  imap_server: string
  port: number
  password: string
  use_ssl: boolean
}

export interface EmailTestResult {
  success: boolean
  message: string
}

export interface EmailFetchResult {
  config_id: number
  total_emails_checked: number
  new_invoices_found: number
  errors: string[]
  status: string
}

export interface EmailFetchLogItem {
  id: number
  config_id: number
  email_address: string | null
  fetch_time: string | null
  total_emails_checked: number
  new_invoices_count: number
  status: string
  error_message: string | null
}

export interface EmailFetchLogPage {
  total: number
  page: number
  page_size: number
  items: EmailFetchLogItem[]
}

/* ---------- API 调用 ---------- */
export function createEmailConfig(data: EmailConfigPayload) {
  return request.post<EmailConfigItem, EmailConfigItem>('/email/configs', data)
}

export function getEmailConfigs() {
  return request.get<EmailConfigItem[], EmailConfigItem[]>('/email/configs')
}

export function updateEmailConfig(id: number, data: EmailConfigUpdatePayload) {
  return request.put<EmailConfigItem, EmailConfigItem>(`/email/configs/${id}`, data)
}

export function deleteEmailConfig(id: number) {
  return request.delete<void, void>(`/email/configs/${id}`)
}

export function testConnection(data: EmailTestPayload) {
  return request.post<EmailTestResult, EmailTestResult>('/email/test-connection', data)
}

export function manualFetch(configId: number) {
  return request.post<EmailFetchResult, EmailFetchResult>(`/email/fetch/${configId}`)
}

export function getFetchLogs(params: { page?: number; pageSize?: number; configId?: number } = {}) {
  return request.get<EmailFetchLogPage, EmailFetchLogPage>('/email/fetch-logs', {
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
      config_id: params.configId,
    },
  })
}
