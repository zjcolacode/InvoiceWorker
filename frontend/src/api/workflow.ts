import request from './request'

export interface WorkflowStartOptions {
  email_fetch?: boolean
  recognize_and_classify?: boolean
  organize?: boolean
}

export interface WorkflowStartResponse {
  task_id: number
  status: string
  message: string
}

export interface WorkflowStepDetail {
  step: string
  key: string
  status: string // pending / processing / completed / failed / skipped
  result?: string | null
  error?: string | null
  started_at?: string | null
  completed_at?: string | null
}

export interface WorkflowStatus {
  task_id: number
  status: string // pending / processing / completed / failed / cancelled
  current_step: string
  progress: number
  steps_detail: WorkflowStepDetail[]
  started_at?: string | null
  completed_at?: string | null
  error_log?: string | null
  invoice_count: number
}

export interface WorkflowHistoryItem {
  task_id: number
  status: string
  started_at?: string | null
  completed_at?: string | null
  invoice_count: number
  error_log?: string | null
  summary?: string | null
}

export interface WorkflowHistoryPage {
  total: number
  page: number
  page_size: number
  items: WorkflowHistoryItem[]
}

/** 启动月度整理流程 */
export function startWorkflow(options: WorkflowStartOptions = {}) {
  return request.post<unknown, WorkflowStartResponse>('/api/workflow/start', {
    email_fetch: options.email_fetch ?? true,
    recognize_and_classify: options.recognize_and_classify ?? true,
    organize: options.organize ?? true,
  })
}

/** 查询流程状态 */
export function getWorkflowStatus(taskId: number) {
  return request.get<unknown, WorkflowStatus>(`/api/workflow/status/${taskId}`)
}

/** 获取历史流程记录 */
export function getWorkflowHistory(params: { page?: number; pageSize?: number } = {}) {
  return request.get<unknown, WorkflowHistoryPage>('/api/workflow/history', {
    params: {
      page: params.page ?? 1,
      page_size: params.pageSize ?? 20,
    },
  })
}

/** 取消正在执行的流程 */
export function cancelWorkflow(taskId: number) {
  return request.post<unknown, { success: boolean; task_id: number; message: string }>(
    `/api/workflow/cancel/${taskId}`,
  )
}
