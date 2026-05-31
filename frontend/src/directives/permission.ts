import type { App, Directive, DirectiveBinding } from 'vue'
import { useUserStore } from '@/stores/user'
import type { Role } from '@/api/auth'

/**
 * v-permission directive
 *
 * Usage:
 *   <button v-permission="['admin']">delete</button>
 *   <a v-permission="['admin','operator']">edit</a>
 *
 * If the current user's role is not in the supplied list,
 * the element is removed from the DOM.
 */
function check(binding: DirectiveBinding<Role[] | string[] | undefined>): boolean {
  const value = binding.value
  if (!value || !Array.isArray(value) || value.length === 0) return true
  const store = useUserStore()
  return store.hasRole(value)
}

function apply(el: HTMLElement, binding: DirectiveBinding) {
  if (!check(binding)) {
    el.parentNode?.removeChild(el)
  }
}

export const permission: Directive = {
  mounted: apply,
  updated(el, binding) {
    // Re-evaluate on update; if blocked, hide.
    if (!check(binding)) {
      el.style.display = 'none'
    } else {
      el.style.display = ''
    }
  },
}

export function setupPermissionDirective(app: App) {
  app.directive('permission', permission)
}

export default permission
