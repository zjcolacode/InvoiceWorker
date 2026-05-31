import request from './request'

export interface GeneratePrintResult {
  filename: string
  download_url: string
  preview_url: string
  invoice_count: number
  page_count: number
}

export interface PrintFile {
  filename: string
  size: number
  created_at: string
  download_url: string
  preview_url: string
}

/**
 * 生成打印PDF
 * @param invoiceIds 发票ID列表
 * @param layout 排版方式, 默认 2_per_page
 */
export function generatePrintPdf(
  invoiceIds: number[],
  layout: string = '2_per_page',
) {
  return request.post<unknown, GeneratePrintResult>(
    '/api/print/generate',
    { invoice_ids: invoiceIds, layout },
    { timeout: 180000 },
  )
}

/**
 * 列出最近生成的打印文件
 */
export function listPrintFiles() {
  return request.get<unknown, PrintFile[]>('/api/print/files')
}

/**
 * 删除指定打印文件
 */
export function deletePrintFile(filename: string) {
  return request.delete<unknown, { success: boolean; filename: string }>(
    `/api/print/files/${encodeURIComponent(filename)}`,
  )
}

/**
 * 清理超过指定天数的打印文件 (admin)
 */
export function cleanPrintFiles(days: number = 7) {
  return request.delete<unknown, { success: boolean; removed: number; days: number }>(
    '/api/print/clean',
    { params: { days } },
  )
}

/**
 * 获取下载URL (供 a 标签 / window.open 使用)
 * 后端校验 Authorization, 因此实际下载需通过带 token 的 fetch/blob 方式。
 */
export function getDownloadUrl(filename: string): string {
  return `/api/print/download/${encodeURIComponent(filename)}`
}

/**
 * 获取预览URL
 */
export function getPreviewUrl(filename: string): string {
  return `/api/print/preview/${encodeURIComponent(filename)}`
}

/**
 * 以 Blob 方式获取打印PDF (用于 iframe 预览或浏览器下载, 自动附带 token)
 * @param mode preview | download
 */
export async function fetchPrintBlob(filename: string, mode: 'preview' | 'download' = 'preview') {
  const url = mode === 'download' ? getDownloadUrl(filename) : getPreviewUrl(filename)
  const token = localStorage.getItem('token') || ''
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  if (!res.ok) {
    throw new Error(`请求失败: ${res.status}`)
  }
  return await res.blob()
}
