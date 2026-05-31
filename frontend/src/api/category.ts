import request from './request'

export interface Category {
  id: number
  name: string
  keywords?: string | null
  description?: string | null
  color: string
  is_active: boolean
  created_at?: string | null
}

export interface CategoryCreatePayload {
  name: string
  keywords?: string | null
  description?: string | null
  color?: string | null
}

export interface CategoryUpdatePayload {
  name?: string
  keywords?: string | null
  description?: string | null
  color?: string | null
  is_active?: boolean
}

export interface ReclassifyResult {
  total: number
  updated: number
  skipped: number
}

/**
 * 获取所有分类
 */
export function getCategories() {
  return request.get<unknown, Category[]>('/api/categories/')
}

/**
 * 创建分类
 */
export function createCategory(data: CategoryCreatePayload) {
  return request.post<unknown, Category>('/api/categories/', data)
}

/**
 * 更新分类
 */
export function updateCategory(id: number, data: CategoryUpdatePayload) {
  return request.put<unknown, Category>(`/api/categories/${id}`, data)
}

/**
 * 删除分类
 */
export function deleteCategory(id: number) {
  return request.delete<unknown, { success: boolean; id: number; name: string }>(
    `/api/categories/${id}`,
  )
}

/**
 * 初始化默认分类(已存在则跳过)
 */
export function initDefaults() {
  return request.post<unknown, { success: boolean; created: number }>(
    '/api/categories/init-defaults',
  )
}

/**
 * 对所有未分类发票批量重新分类
 */
export function reclassify() {
  return request.post<unknown, ReclassifyResult>('/api/categories/reclassify')
}
