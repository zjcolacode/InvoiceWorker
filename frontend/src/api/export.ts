import request from './request'

export type ExportMode = 'monthly_summary' | 'category_summary' | 'detail'

export interface ExportRequestPayload {
  mode: ExportMode
  year: number
  month: number
  category?: string
  source_type?: string
}

export interface ExportResult {
  filename: string
  download_url: string
  record_count: number
}

export interface ExportFile {
  filename: string
  size: number
  created_at: string
  mode?: string | null
  download_url: string
}

/**
 * 生成 Excel 导出文件
 */
export function generateExport(data: ExportRequestPayload) {
  return request.post<unknown, ExportResult>('/api/export/generate', data, {
    timeout: 120000,
  })
}

/**
 * 获取导出历史
 */
export function getExportHistory() {
  return request.get<unknown, ExportFile[]>('/api/export/history')
}

/**
 * 删除导出文件
 */
export function deleteExportFile(filename: string) {
  return request.delete<unknown, { success: boolean; filename: string }>(
    `/api/export/files/${encodeURIComponent(filename)}`,
  )
}

/**
 * 下载 URL (后端校验 token，需通过带 Authorization 的 fetch 触发)
 */
export function getExportDownloadUrl(filename: string): string {
  return `/api/export/download/${encodeURIComponent(filename)}`
}

/**
 * 触发浏览器下载（自动附带 token）
 * 1. fetch blob
 * 2. 创建临时 a 标签触发下载
 */
export async function downloadExport(filename: string): Promise<void> {
  const url = getExportDownloadUrl(filename)
  const token = localStorage.getItem('token') || ''
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  if (!res.ok) {
    throw new Error(`下载失败: ${res.status}`)
  }
  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  // 释放 URL
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}
