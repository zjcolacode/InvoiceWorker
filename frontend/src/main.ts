import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './style.css'
import { setupPermissionDirective } from './directives/permission'

const app = createApp(App)

// Pinia must be installed BEFORE the router so route guards
// (which call useUserStore()) can resolve synchronously.
app.use(createPinia())

// Element Plus + Chinese locale
app.use(ElementPlus, { locale: zhCn })

// Register all Element Plus icons globally
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component as any)
}

// Custom directives (e.g. v-permission)
setupPermissionDirective(app)

app.use(router)

app.mount('#app')
