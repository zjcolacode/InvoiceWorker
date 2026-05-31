import request from './request'
import type { Role, UserInfo } from './auth'

export interface UserListParams {
  page?: number
  page_size?: number
}

export interface UserListResponse {
  items: UserInfo[]
  total: number
  page: number
  page_size: number
}

export interface CreateUserPayload {
  username: string
  password: string
  role: Role
  email?: string | null
  menu_permissions?: string[] | null
}

export interface UpdateUserPayload {
  username?: string
  role?: Role
  email?: string | null
  password?: string
  is_active?: boolean
}

export interface MenuItem {
  path: string
  title: string
  roles?: Role[] | null
}

/** GET /api/users/ — paged user list */
export function getUsers(params?: UserListParams) {
  return request.get<unknown, UserListResponse>('/api/users/', { params })
}

/** POST /api/users/ — create user */
export function createUser(data: CreateUserPayload) {
  return request.post<unknown, UserInfo>('/api/users/', data)
}

/** PUT /api/users/{id} — update user */
export function updateUser(id: number, data: UpdateUserPayload) {
  return request.put<unknown, UserInfo>(`/api/users/${id}`, data)
}

/** DELETE /api/users/{id} — delete user */
export function deleteUser(id: number) {
  return request.delete<unknown, void>(`/api/users/${id}`)
}

/** PUT /api/users/{id}/permissions — assign menu permissions */
export function updateUserPermissions(id: number, permissions: string[]) {
  return request.put<unknown, UserInfo>(`/api/users/${id}/permissions`, {
    permissions,
  })
}

/** GET /api/users/menus — list all assignable menus */
export function getMenuList() {
  return request.get<unknown, MenuItem[]>('/api/users/menus')
}
