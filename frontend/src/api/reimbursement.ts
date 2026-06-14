import request from './request'

// ============================================================
// 类型定义
// ============================================================

/** 全量发票明细单中的一条明细记录（19 列，对应「发票基础信息」工作表） */
export interface InvoiceDetailItem {
  id: number
  upload_batch_id: number
  serial_no?: string | null
  invoice_code?: string | null
  invoice_no?: string | null
  digital_invoice_no?: string | null
  seller_tax_no?: string | null
  seller_name?: string | null
  buyer_tax_no?: string | null
  buyer_name?: string | null
  invoice_date?: string | null
  amount?: string | null
  tax_amount?: string | null
  total_amount?: string | null
  invoice_source?: string | null
  invoice_type?: string | null
  invoice_status?: string | null
  is_positive?: string | null
  risk_level?: string | null
  issuer?: string | null
  remark?: string | null
  goods_or_service_name?: string | null
  verify_status?: string | null
  verified_at?: string | null
  match_method?: string | null
  reimburse_status?: string | null
  created_at?: string | null
}

export interface InvoiceDetailListResult {
  total: number
  page: number
  page_size: number
  items: InvoiceDetailItem[]
}

export interface UploadDetailResult {
  batch_id: number
  filename: string
  total_count: number
  skipped_count: number
}

export interface VerifyResult {
  total_count: number
  matched_count: number
  unmatched_count: number
  unmatched_details: string[]
}

export interface UploadLogItem {
  id: number
  original_filename: string
  total_count: number
  uploaded_by?: number | null
  uploader_username?: string | null
  created_at?: string | null
}

export interface UploadLogListResult {
  total: number
  page: number
  page_size: number
  items: UploadLogItem[]
}

export interface DetailQueryParams {
  keyword?: string
  invoice_source?: string
  invoice_type?: string
  verify_status?: string
  start_date?: string
  end_date?: string
  upload_batch_id?: number
  page?: number
  page_size?: number
}

// ============================================================
// 新版 API（全量明细 + 核销）
// ============================================================

/**
 * 上传全量发票明细单（仅入库，不执行核销）
 */
export function uploadInvoiceDetail(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<unknown, UploadDetailResult>(
    '/api/reimbursement/upload-detail',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    },
  )
}

/**
 * 对所有待核销明细执行核销
 */
export function verifyInvoices() {
  return request.post<unknown, VerifyResult>(
    '/api/reimbursement/verify',
    undefined,
    { timeout: 120000 },
  )
}

/**
 * 分页查询全量发票明细
 */
export function getInvoiceDetails(params: DetailQueryParams) {
  const query: Record<string, string | number | undefined> = {
    keyword: params.keyword || undefined,
    invoice_source: params.invoice_source || undefined,
    invoice_type: params.invoice_type || undefined,
    verify_status: params.verify_status || undefined,
    start_date: params.start_date || undefined,
    end_date: params.end_date || undefined,
    upload_batch_id: params.upload_batch_id ?? undefined,
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  }
  return request.get<unknown, InvoiceDetailListResult>(
    '/api/reimbursement/details',
    { params: query },
  )
}

/**
 * 批量提交报销
 */
export function submitReimburse(ids: number[]) {
  return request.post<unknown, { success: boolean; updated_count: number; total_requested: number }>(
    '/api/reimbursement/submit-reimburse',
    { ids },
  )
}

// ============================================================
// 报销申请
// ============================================================

/** 报销申请明细项 */
export interface ReimburseDetailItem {
  date?: string
  content?: string
  receipt_count: number
  amount: number
  remark?: string
}

/** 报销申请创建参数 */
export interface ReimburseApplicationCreate {
  reimburse_date: string
  department: string
  category: string
  reason: string
  remark?: string
  invoice_ids: number[]
  detail_items: ReimburseDetailItem[]
}

/** 报销申请响应 */
export interface ReimburseApplicationResponse {
  id: number
  reimburse_no: string
  applicant_name: string
  applicant_position?: string | null
  reimburse_date: string
  department: string
  category: string
  reason: string
  remark?: string | null
  total_amount: number
  invoice_ids: number[]
  status: string
  created_at?: string | null
}

/** 创建报销申请 */
export function createReimburseApplication(data: ReimburseApplicationCreate) {
  return request.post<unknown, ReimburseApplicationResponse>(
    '/api/reimbursement/create-reimburse-application',
    data,
  )
}

/** 获取报销申请记录列表 */
export interface ReimburseApplicationListItem {
  id: number
  reimburse_no: string
  applicant_name: string
  applicant_position?: string | null
  reimburse_date?: string | null
  department?: string | null
  category?: string | null
  total_amount?: number | null
  status?: string | null
  created_at?: string | null
}

export function getReimburseApplications(params: { page: number; page_size: number }) {
  return request.get<unknown, { total: number; page: number; page_size: number; items: ReimburseApplicationListItem[] }>(
    '/api/reimbursement/reimburse-applications',
    { params },
  )
}

/**
 * 分页查询上传历史
 */
export function getUploadLogs(params: { page?: number; page_size?: number }) {
  const query: Record<string, string | number | undefined> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  }
  return request.get<unknown, UploadLogListResult>(
    '/api/reimbursement/upload-logs',
    { params: query },
  )
}

// ============================================================
// 旧版 API（向后兼容，保留）
// ============================================================

export interface ReimbursementResult {
  total_count: number
  matched_count: number
  unmatched_count: number
  unmatched_details: string[]
}

export interface ReimbursementRecord {
  id: number
  original_filename: string
  uploaded_by?: number | null
  uploader_username?: string | null
  total_count: number
  matched_count: number
  unmatched_count: number
  unmatched_details?: string[] | null
  created_at?: string | null
}

export interface ReimbursementRecordListResult {
  total: number
  page: number
  page_size: number
  items: ReimbursementRecord[]
}

/**
 * 上传发票明细清单并执行核销（旧接口）
 */
export function uploadReimbursementFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<unknown, ReimbursementResult>(
    '/api/reimbursement/upload',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    },
  )
}

/**
 * 获取核销历史记录（保留旧接口）
 */
export function getReimbursementRecords(params: { page?: number; pageSize?: number }) {
  const query: Record<string, string | number | undefined> = {
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
  }
  return request.get<unknown, ReimbursementRecordListResult>(
    '/api/reimbursement/records',
    { params: query },
  )
}

// ============================================================
// 报销单管理 - 独立邮箱相关
// ============================================================

/** 邮箱配置 */
export interface ReimbEmailConfig {
  id: number
  email_address: string
  imap_server: string
  port: number
  use_ssl: boolean
  is_active: boolean
  last_check_at: string | null
  created_at: string | null
}

export interface ReimbEmailConfigCreate {
  email_address: string
  imap_server: string
  port: number
  password: string
  use_ssl: boolean
}

export interface ReimbEmailConfigUpdate {
  email_address?: string
  imap_server?: string
  port?: number
  password?: string
  use_ssl?: boolean
  is_active?: boolean
}

/** 邮件消息 */
export interface ReimbEmailMessage {
  id: number
  config_id: number
  message_uid: string | null
  subject: string | null
  sender: string | null
  received_at: string | null
  attachment_name: string | null
  file_size: number | null
  created_at: string | null
}

/** 拉取日志 */
export interface ReimbEmailFetchLog {
  id: number
  config_id: number
  email_address: string | null
  fetch_time: string | null
  total_emails_checked: number
  new_emails_count: number
  status: string
  error_message: string | null
}

/** 测试连接结果 */
export interface ReimbEmailTestResult {
  success: boolean
  message: string
}

/** 拉取请求参数 */
export interface ReimbEmailFetchRequest {
  date_from?: string
  date_to?: string
  keyword?: string
  has_attachment?: boolean
}

/** 拉取结果 */
export interface ReimbEmailFetchResult {
  success: boolean
  total_checked: number
  new_count: number
  skipped: number
}

// --- 邮箱配置 CRUD ---

export function getReimbEmailConfigs() {
  return request.get<unknown, ReimbEmailConfig[]>('/api/reimbursement/email-configs')
}

export function createReimbEmailConfig(data: ReimbEmailConfigCreate) {
  return request.post<unknown, ReimbEmailConfig>('/api/reimbursement/email-configs', data)
}

export function updateReimbEmailConfig(id: number, data: ReimbEmailConfigUpdate) {
  return request.put<unknown, ReimbEmailConfig>(`/api/reimbursement/email-configs/${id}`, data)
}

export function deleteReimbEmailConfig(id: number) {
  return request.delete(`/api/reimbursement/email-configs/${id}`)
}

export function testReimbEmailConnection(configId: number) {
  return request.post<unknown, ReimbEmailTestResult>(`/api/reimbursement/email-configs/${configId}/test`)
}

// --- 邮件拉取 ---

export function fetchReimbEmails(configId: number, params: ReimbEmailFetchRequest) {
  return request.post<unknown, ReimbEmailFetchResult>(`/api/reimbursement/email-fetch/${configId}`, params)
}

// --- 邮件消息列表 ---

export function getReimbEmailMessages(params: { page?: number; page_size?: number; config_id?: number }) {
  return request.get<unknown, { total: number; items: ReimbEmailMessage[] }>('/api/reimbursement/email-messages', { params })
}

// --- 拉取日志 ---

export function getReimbEmailFetchLogs(params: { page?: number; page_size?: number }) {
  return request.get<unknown, { total: number; items: ReimbEmailFetchLog[] }>('/api/reimbursement/email-fetch-logs', { params })
}

// ============================================================
// 手工匹配
// ============================================================

export interface ManualMatchResult {
  success: boolean
  recognized_invoice_no: string | null
  recognized_data: Record<string, any> | null
  match_result: string  // matched / not_matched / recognition_failed
  message: string
}

export interface ManualMatchRecord {
  id: number
  invoice_detail_id: number
  original_filename: string
  recognized_invoice_no: string | null
  match_status: string
  operated_by: number | null
  created_at: string | null
}

/** 手工匹配 - 上传文件并识别匹配 */
export function manualMatchInvoice(detailId: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<unknown, ManualMatchResult>(
    `/api/reimbursement/manual-match/${detailId}`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000, // 识别可能耗时较长
    },
  )
}

/** 获取手工匹配记录 */
export function getManualMatchRecords(params: { page?: number; page_size?: number }) {
  const query: Record<string, string | number | undefined> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  }
  return request.get<unknown, { total: number; items: ManualMatchRecord[] }>(
    '/api/reimbursement/manual-match-records',
    { params: query },
  )
}
