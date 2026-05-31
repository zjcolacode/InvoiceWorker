import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authApi from '@/api/auth'
import type { Role, UserInfo } from '@/api/auth'

const TOKEN_KEY = 'token'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const userInfo = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => Boolean(token.value))
  const role = computed<Role | ''>(() => userInfo.value?.role ?? '')
  const username = computed(() => userInfo.value?.username ?? '')

  /** Persist token to localStorage and store. */
  function setToken(newToken: string) {
    token.value = newToken
    if (newToken) localStorage.setItem(TOKEN_KEY, newToken)
    else localStorage.removeItem(TOKEN_KEY)
  }

  /** Login → token → fetch profile. */
  async function login(u: string, p: string) {
    const res = await authApi.login(u, p)
    setToken(res.access_token)
    await getUserInfo()
    return res
  }

  /** Fetch current user profile. */
  async function getUserInfo() {
    const res = await authApi.getUserInfo()
    userInfo.value = res
    return res
  }

  /** Clear token + identity. */
  function logout() {
    setToken('')
    userInfo.value = null
  }

  /**
   * Role gate. Pass an array of allowed roles.
   * Empty / undefined input → permit (no restriction).
   */
  function hasRole(roles?: Role[] | string[]): boolean {
    if (!roles || roles.length === 0) return true
    if (!userInfo.value) return false
    return roles.includes(userInfo.value.role as Role)
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    role,
    username,
    setToken,
    login,
    logout,
    getUserInfo,
    hasRole,
  }
})
