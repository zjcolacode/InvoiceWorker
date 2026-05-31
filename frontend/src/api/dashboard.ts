import request from './request'

export interface CategoryItem {
  name: string
  count: number
  amount: number
}

export interface TrendItem {
  month: string
  count: number
  amount: number
}

export interface RecentInvoiceItem {
  id: number
  invoice_no?: string | null
  invoice_date?: string | null
  seller_name?: string | null
  total?: number | null
  category?: string | null
  status: string
  created_at?: string | null
}

export interface DashboardStats {
  total_invoices: number
  total_amount: number
  pending_count: number
  recognized_count: number
  category_distribution: CategoryItem[]
  recent_invoices: RecentInvoiceItem[]
  monthly_trend: TrendItem[]
}

export interface ActivityLogItem {
  id: number
  task_type: string
  status: string
  started_at?: string | null
  completed_at?: string | null
  invoice_count: number
  error_log?: string | null
  created_at?: string | null
}

export interface ActivityLogPage {
  total: number
  page: number
  page_size: number
  items: ActivityLogItem[]
}

/** 获取仪表盘统计数据 */
export function getDashboardStats() {
  return request.get<unknown, DashboardStats>('/api/dashboard/stats')
}

/** 获取操作日志(分页) */
export function getActivityLog(params: { page?: number; pageSize?: number } = {}) {
  return request.get<unknown, ActivityLogPage>('/api/dashboard/activity-log', {
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
    },
  })
}
