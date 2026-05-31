<template>
  <div class="auth">
    <!-- ═════════════ LEFT · Editorial cover ═════════════ -->
    <aside class="auth__cover">
      <div class="cover__top">
        <div class="cover__brand">
          <span class="stamp cover__stamp">整</span>
          <div>
            <div class="eyebrow">Invoice · Worker · Console</div>
            <div class="cover__system">v1.0.0 — Edition 一</div>
          </div>
        </div>
        <div class="serial">{{ todayStamp }}</div>
      </div>

      <div class="cover__center">
        <p class="eyebrow cover__eyebrow">— 发票整理 · 数字员工</p>
        <h1 class="cover__title">
          <span class="cover__line">让每一张</span>
          <span class="cover__line cover__line--em"><em>票据</em>，</span>
          <span class="cover__line">归于其</span>
          <span class="cover__line cover__line--em"><em>位</em>。</span>
        </h1>

        <p class="cover__caption">
          自动识别、智能归档、合规存留 ——<br />
          为现代财务团队打造的安静工具。
        </p>

        <div class="cover__rule" />

        <ul class="ledger-rows">
          <li v-for="(row, i) in rows" :key="i" class="ledger-row">
            <span class="ledger-row__no">№ {{ String(row.no).padStart(4, '0') }}</span>
            <span class="ledger-row__title">{{ row.title }}</span>
            <span class="ledger-row__amt">{{ row.amount }}</span>
          </li>
        </ul>
      </div>

      <div class="cover__foot">
        <div class="serial">— 安全 · 可审计 · 离线优先 —</div>
        <div class="ticks">
          <span class="ticks__bar" />
          <span class="ticks__bar" />
          <span class="ticks__bar ticks__bar--em" />
          <span class="ticks__bar" />
          <span class="ticks__bar" />
          <span class="ticks__bar" />
          <span class="ticks__bar ticks__bar--em" />
          <span class="ticks__bar" />
        </div>
      </div>

      <!-- decorative hanko -->
      <div class="hanko" aria-hidden="true">
        <div class="hanko__inner">登 录</div>
      </div>
    </aside>

    <!-- ═════════════ RIGHT · Form ═════════════ -->
    <section class="auth__panel">
      <div class="panel__top serial">
        <span>FORM · 0001</span>
        <span>access · session</span>
      </div>

      <div class="panel__body">
        <p class="eyebrow">Authenticate</p>
        <h2 class="panel__title">请<em>登录</em>以继续</h2>
        <p class="panel__sub">凭证将仅用于本会话，不会留存于浏览器。</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          class="login-form"
          @submit.prevent="onSubmit"
        >
          <el-form-item label="用户名 · USERNAME" prop="username">
            <el-input
              v-model="form.username"
              placeholder="例如 admin"
              autocomplete="username"
              clearable
              @keyup.enter="onSubmit"
            />
          </el-form-item>

          <el-form-item label="密码 · PASSWORD" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="至少 6 位"
              autocomplete="current-password"
              show-password
              @keyup.enter="onSubmit"
            />
          </el-form-item>

          <div class="row-flex">
            <span class="serial">REMEMBER · {{ today }}</span>
            <span class="serial">{{ nowStamp }}</span>
          </div>

          <el-button
            type="primary"
            class="submit-btn"
            :loading="loading"
            native-type="submit"
            @click="onSubmit"
          >
            <span class="submit-btn__text">进入系统</span>
            <span class="submit-btn__arrow">→</span>
          </el-button>

          <div class="hint">
            <span class="hint__dot" />
            首次使用？请联系管理员开通账号。
          </div>
        </el-form>
      </div>

      <div class="panel__foot serial">
        <span>© 2026 · INVOICE · WORKER</span>
        <span>BUILT WITH <em class="heart">♥</em> · KYOTO ↔ 上海</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const store = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, message: '用户名至少 2 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
}

async function onSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await store.login(form.username, form.password)
    ElMessage.success(`欢迎回来，${store.username}`)
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.replace(redirect)
  } catch {
    /* error already toasted by interceptor */
  } finally {
    loading.value = false
  }
}

// ───── decorative ledger rows
const rows = [
  { no: 1, title: '差旅 · 京都出張', amount: '¥ 8,420.00' },
  { no: 2, title: '订阅 · 设计软件', amount: '¥   299.00' },
  { no: 3, title: '采办 · 办公耗材', amount: '¥ 1,205.50' },
  { no: 4, title: '会议 · 茶水餐饮', amount: '¥   486.00' },
]

const today = computed(() => {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
})
const todayStamp = computed(() => {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`
})

const now = ref(new Date())
const nowStamp = computed(() => {
  const d = now.value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
})
let timer: number | undefined
onMounted(() => { timer = window.setInterval(() => { now.value = new Date() }, 1000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.auth {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  min-height: 100vh;
  background: var(--paper);
}

/* ═════════════ Cover (left) ═════════════ */
.auth__cover {
  position: relative;
  padding: 36px 56px 32px;
  display: flex;
  flex-direction: column;
  background: var(--paper);
  border-right: var(--hair);
  background-image:
    repeating-linear-gradient(0deg, transparent 0 39px, var(--rule-faint) 39px 40px);
  overflow: hidden;
}

.cover__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.cover__brand { display: flex; gap: 14px; align-items: center; }
.cover__stamp { width: 48px; height: 48px; font-size: 22px; }
.cover__system {
  font-family: var(--serif);
  font-style: italic;
  font-size: 18px;
  margin-top: 2px;
}

.cover__center {
  margin: auto 0;
  padding: 40px 0;
  max-width: 540px;
  animation: rise 0.7s ease both;
}
.cover__eyebrow { margin-bottom: 18px; display: block; }
.cover__title {
  font-family: var(--serif);
  font-weight: 300;
  font-size: clamp(46px, 5.4vw, 78px);
  line-height: 1.02;
  letter-spacing: -0.025em;
  margin: 0 0 28px;
  color: var(--ink);
}
.cover__line { display: block; }
.cover__line em {
  font-style: italic;
  color: var(--ink);
}
.cover__line--em em {
  position: relative;
}
.cover__line--em em::after {
  content: '';
  position: absolute;
  left: -2%;
  right: -2%;
  bottom: 0.08em;
  height: 12px;
  background: var(--stamp);
  opacity: 0.18;
  z-index: -1;
  transform: skewX(-8deg);
}

.cover__caption {
  font-size: 15px;
  line-height: 1.7;
  color: var(--mute);
  max-width: 420px;
  margin-bottom: 32px;
}

.cover__rule {
  height: 1px;
  background: var(--rule);
  width: 60px;
  margin: 0 0 22px;
}

.ledger-rows {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: var(--hair-soft);
  max-width: 460px;
}
.ledger-row {
  display: grid;
  grid-template-columns: 90px 1fr auto;
  align-items: center;
  gap: 14px;
  padding: 11px 0;
  border-bottom: var(--hair-soft);
  font-family: var(--mono);
  font-size: 12px;
  color: var(--mute);
  font-variant-numeric: tabular-nums;
}
.ledger-row__no { letter-spacing: 0.05em; color: var(--ink); }
.ledger-row__title { font-family: var(--sans); color: var(--ink-2); font-size: 13px; }
.ledger-row__amt { color: var(--stamp); font-weight: 500; }

.cover__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding-top: 24px;
}
.ticks {
  display: inline-flex;
  align-items: flex-end;
  gap: 4px;
  height: 14px;
}
.ticks__bar {
  width: 2px;
  height: 6px;
  background: var(--rule);
  display: inline-block;
}
.ticks__bar--em { height: 14px; background: var(--stamp); }

/* hanko in corner */
.hanko {
  position: absolute;
  right: -28px;
  top: 96px;
  width: 132px;
  height: 132px;
  border: 2px solid var(--stamp);
  background: rgba(184, 65, 14, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  transform: rotate(8deg);
  pointer-events: none;
  border-radius: 4px;
  animation: stamp 1.1s cubic-bezier(0.2, 1.2, 0.3, 1) 0.4s both;
}
.hanko__inner {
  font-family: var(--serif);
  font-size: 36px;
  color: var(--stamp);
  font-weight: 500;
  letter-spacing: 0.2em;
  text-align: center;
  line-height: 1.05;
}
@keyframes stamp {
  0% { opacity: 0; transform: rotate(28deg) scale(1.5); }
  60% { opacity: 1; transform: rotate(6deg) scale(0.94); }
  100% { opacity: 1; transform: rotate(8deg) scale(1); }
}
@keyframes rise {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ═════════════ Panel (right) ═════════════ */
.auth__panel {
  background: var(--paper-2);
  display: flex;
  flex-direction: column;
  padding: 36px 64px 32px;
  position: relative;
}
.auth__panel::before {
  content: '';
  position: absolute;
  top: 0; bottom: 0; left: 0;
  width: 1px;
  background: repeating-linear-gradient(180deg, var(--rule) 0 4px, transparent 4px 8px);
  opacity: 0.3;
}

.panel__top {
  display: flex;
  justify-content: space-between;
  text-transform: uppercase;
}
.panel__body {
  margin: auto 0;
  max-width: 420px;
  width: 100%;
  align-self: center;
  animation: rise 0.7s 0.1s ease both;
}
.panel__title {
  font-family: var(--serif);
  font-weight: 300;
  font-size: 44px;
  letter-spacing: -0.02em;
  margin: 12px 0 8px;
  color: var(--ink);
}
.panel__title em { font-style: italic; color: var(--stamp); }
.panel__sub {
  font-size: 14px;
  color: var(--mute);
  margin-bottom: 32px;
}

.login-form { display: flex; flex-direction: column; gap: 8px; }
:deep(.el-form-item) { margin-bottom: 22px !important; }

.row-flex {
  display: flex;
  justify-content: space-between;
  margin: -2px 0 22px;
  font-variant-numeric: tabular-nums;
}

.submit-btn {
  width: 100%;
  height: 52px !important;
  font-size: 13px !important;
  letter-spacing: 0.2em !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 14px !important;
}
.submit-btn :deep(span) { display: inline-flex; align-items: center; gap: 14px; }
.submit-btn__arrow {
  font-family: var(--serif);
  font-style: italic;
  font-size: 18px;
  letter-spacing: 0;
  transition: transform 0.25s ease;
}
.submit-btn:hover .submit-btn__arrow { transform: translateX(6px); }

.hint {
  margin-top: 22px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--mute);
}
.hint__dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--stamp);
  flex-shrink: 0;
}

.panel__foot {
  display: flex;
  justify-content: space-between;
  text-transform: uppercase;
  color: var(--mute);
}
.heart { color: var(--stamp); font-style: normal; }

/* responsive */
@media (max-width: 960px) {
  .auth { grid-template-columns: 1fr; }
  .auth__cover { padding: 28px 24px; border-right: 0; border-bottom: var(--hair); }
  .hanko { right: -40px; top: 24px; width: 96px; height: 96px; }
  .hanko__inner { font-size: 26px; }
  .auth__panel { padding: 32px 24px; }
  .panel__title { font-size: 36px; }
  .ledger-rows { display: none; }
  .cover__center { padding: 24px 0; }
}
</style>
