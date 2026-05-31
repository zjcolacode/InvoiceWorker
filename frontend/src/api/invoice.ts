import request from './request'

export interface Invoice {
  id: number
  invoice_no?: string | null
  invoice_date?: string | null
  seller_name?: string | null
  buyer_name?: string | null
  amount?: number | null
  tax?: number | null
  total?: number | null
  items?: string | null
  category?: string | null
  source_type: string
  file_path?: string | null
  original_filename?: string | null
  recognized_at?: string | null
  status: string
  user_id?: number | null
  /** 上传者用户名（仅 admin 查看列表时返回） */
  uploader_username?: string | null
  created_at?: string | null
}

export interface InvoiceListParams {
  page?: number
  pageSize?: number
  category?: string
  sourceType?: string
  status?: string
  dateFrom?: string
  dateTo?: string
  keyword?: string
  /** 仅 admin 可用：按上传者 user_id 过滤 */
  ownerUserId?: number | null
}

export interface InvoiceListResult {
  total: number
  page: number
  page_size: number
  items: Invoice[]
}

export interface InvoiceStats {
  month: string
  month_count: number
  month_total: number
  categories: Array<{
    category: string
    count: number
    amount: number
    percent: number
  }>
}

export interface SkippedFile {
  filename: string
  reason: string
  existing_id?: number | null
}

export interface InvoiceUploadResult {
  uploaded: Invoice[]
  skipped: SkippedFile[]
  message: string
}

/**
 * 上传发票文件 (支持多文件)
 * @param files 文件数组
 * @param sourceType 来源类型 pdf | paper
 */
export function uploadInvoices(files: File[], sourceType: string) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  formData.append('source_type', sourceType)
  return request.post<unknown, InvoiceUploadResult>('/api/invoices/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

/**
 * 获取发票列表
 */
export function getInvoiceList(params: InvoiceListParams) {
  const query: Record<string, string | number | undefined> = {
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
    category: params.category || undefined,
    source_type: params.sourceType || undefined,
    status: params.status || undefined,
    date_from: params.dateFrom || undefined,
    date_to: params.dateTo || undefined,
    keyword: params.keyword || undefined,
    owner_user_id: params.ownerUserId ?? undefined,
  }
  return request.get<unknown, InvoiceListResult>('/api/invoices/', { params: query })
}

/**
 * 获取发票详情
 */
export function getInvoiceDetail(id: number) {
  return request.get<unknown, Invoice>(`/api/invoices/${id}`)
}

/**
 * 删除发票
 */
export function deleteInvoice(id: number) {
  return request.delete<unknown, { success: boolean; id: number; file_deleted: boolean }>(
    `/api/invoices/${id}`,
  )
}

/**
 * 获取统计摘要
 */
export function getInvoiceStats() {
  return request.get<unknown, InvoiceStats>('/api/invoices/stats/summary')
}

/**
 * 触发发票识别（AI识别耗时较长，设置120秒超时）
 */
export function recognizeInvoice(id: number) {
  return request.post<unknown, { success: boolean; data?: unknown; error?: string }>(
    `/api/recognition/recognize/${id}`,
    undefined,
    { timeout: 120000 },
  )
}

/**
 * 更新发票分类
 */
export function updateInvoiceCategory(id: number, category: string) {
  return request.patch<unknown, { success: boolean; id: number; category: string | null }>(
    `/api/invoices/${id}/category`,
    { category },
  )
}
