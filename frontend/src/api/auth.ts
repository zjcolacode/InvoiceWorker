import request from './request'

export type Role = 'admin' | 'operator' | 'viewer'

export interface UserInfo {
  id: number
  username: string
  email: string
  role: Role
  is_active: boolean
  menu_permissions?: string[] | null
  created_at?: string | null
  full_name?: string | null
  position?: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface RegisterPayload {
  username: string
  password: string
  email: string
  role?: Role
}

/** POST /api/auth/login */
export function login(username: string, password: string) {
  return request.post<unknown, LoginResponse>('/api/auth/login', {
    username,
    password,
  })
}

/** GET /api/auth/me */
export function getUserInfo() {
  return request.get<unknown, UserInfo>('/api/auth/me')
}

/** POST /api/auth/register */
export function register(data: RegisterPayload) {
  return request.post<unknown, UserInfo>('/api/auth/register', data)
}
