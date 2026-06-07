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

export interface EmailFetchTaskCreated {
  task_id: string
  config_id: number
  status: string
}

export interface EmailFetchProgress {
  task_id: string
  config_id: number | null
  status: 'running' | 'success' | 'partial' | 'failed' | string
  stage: 'queued' | 'connecting' | 'searching' | 'downloading' | 'finished' | string
  total: number
  processed: number
  total_emails_checked: number
  skipped_existing: number
  new_invoices_found: number
  email_address: string | null
  errors: string[]
  started_at: number | null
  finished_at: number | null
  result: EmailFetchResult | null
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

export interface EmailMessageItem {
  id: number
  config_id: number
  subject: string | null
  sender: string | null
  received_at: string | null
  attachment_name: string | null
  file_size: number
  is_imported: boolean
  imported_at: string | null
  created_at: string | null
}

export interface EmailMessagePage {
  total: number
  page: number
  page_size: number
  items: EmailMessageItem[]
}

export interface EmailMessageImportResult {
  success: boolean
  imported_count: number
  skipped_count: number
  requested: number
}

export interface EmailFetchFilter {
  keyword?: string
  date_from?: string
  date_to?: string
  sender?: string
  has_attachment?: boolean
}

/* ---------- API 调用 ---------- */
export function createEmailConfig(data: EmailConfigPayload) {
  return request.post<EmailConfigItem, EmailConfigItem>('/api/email/configs', data)
}

export function getEmailConfigs() {
  return request.get<EmailConfigItem[], EmailConfigItem[]>('/api/email/configs')
}

export function updateEmailConfig(id: number, data: EmailConfigUpdatePayload) {
  return request.put<EmailConfigItem, EmailConfigItem>(`/api/email/configs/${id}`, data)
}

export function deleteEmailConfig(id: number) {
  return request.delete<void, void>(`/api/email/configs/${id}`)
}

export function testConnection(data: EmailTestPayload) {
  return request.post<EmailTestResult, EmailTestResult>('/api/email/test-connection', data)
}

export function manualFetch(configId: number, filter?: EmailFetchFilter) {
  return request.post<EmailFetchTaskCreated, EmailFetchTaskCreated>(
    `/api/email/fetch/${configId}`,
    filter ?? {},
  )
}

export function getFetchProgress(taskId: string) {
  return request.get<EmailFetchProgress, EmailFetchProgress>(
    `/api/email/fetch-progress/${taskId}`,
  )
}

export function getFetchLogs(params: { page?: number; pageSize?: number; configId?: number } = {}) {
  return request.get<EmailFetchLogPage, EmailFetchLogPage>('/api/email/fetch-logs', {
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
      config_id: params.configId,
    },
  })
}

export function getEmailMessages(
  params: {
    page?: number
    pageSize?: number
    isImported?: boolean
    configId?: number
  } = {},
) {
  return request.get<EmailMessagePage, EmailMessagePage>('/api/email/messages', {
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
      is_imported: params.isImported,
      config_id: params.configId,
    },
  })
}

export function importEmailMessages(messageIds: number[]) {
  return request.post<EmailMessageImportResult, EmailMessageImportResult>(
    '/api/email/messages/import',
    { message_ids: messageIds },
  )
}

export function deleteEmailMessage(id: number) {
  return request.delete<void, void>(`/api/email/messages/${id}`)
}
