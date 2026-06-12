import request from './request'

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
 * 上传发票明细清单并执行核销
 */
export function uploadReimbursementFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<unknown, ReimbursementResult>('/api/reimbursement/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

/**
 * 获取核销历史记录（分页）
 */
export function getReimbursementRecords(params: { page?: number; pageSize?: number }) {
  const query: Record<string, string | number | undefined> = {
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
  }
  return request.get<unknown, ReimbursementRecordListResult>('/api/reimbursement/records', {
    params: query,
  })
}
