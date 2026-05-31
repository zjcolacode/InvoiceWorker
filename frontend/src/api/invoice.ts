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

/**
 * 上传发票文件 (支持多文件)
 * @param files 文件数组
 * @param sourceType 来源类型 pdf | paper
 */
export function uploadInvoices(files: File[], sourceType: string) {
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))
  formData.append('source_type', sourceType)
  return request.post<unknown, Invoice[]>('/invoices/upload', formData, {
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
  }
  return request.get<unknown, InvoiceListResult>('/invoices/', { params: query })
}

/**
 * 获取发票详情
 */
export function getInvoiceDetail(id: number) {
  return request.get<unknown, Invoice>(`/invoices/${id}`)
}

/**
 * 删除发票
 */
export function deleteInvoice(id: number) {
  return request.delete<unknown, { success: boolean; id: number; file_deleted: boolean }>(
    `/invoices/${id}`,
  )
}

/**
 * 获取统计摘要
 */
export function getInvoiceStats() {
  return request.get<unknown, InvoiceStats>('/invoices/stats/summary')
}

/**
 * 触发发票识别
 */
export function recognizeInvoice(id: number) {
  return request.post<unknown, { success: boolean; data?: unknown; error?: string }>(
    `/recognition/recognize/${id}`,
  )
}
