<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = withDefaults(defineProps<{
  serial?: string
  title: string
  caption?: string
  subtitle?: string
}>(), {
  serial: '§',
  caption: '本节即将上线 — 数据正在归档之中。',
  subtitle: '',
})

const route = useRoute()
const titleStr = computed(() => props.title || (route.meta?.title as string) || '—')
</script>

<template>
  <article class="placeholder">
    <header class="ph__head">
      <div class="ph__left">
        <span class="serial ph__serial">{{ serial }} · {{ titleStr }}</span>
        <h1 class="ph__title">
          <span>{{ titleStr }}</span>
          <em v-if="subtitle">{{ subtitle }}</em>
        </h1>
        <p class="ph__caption">{{ caption }}</p>
      </div>
      <div class="ph__right">
        <slot name="actions" />
      </div>
    </header>

    <div class="ph__rule" />

    <section class="ph__body">
      <slot>
        <div class="ph__empty">
          <div class="ph__empty-mark">
            <span class="stamp">空</span>
          </div>
          <p class="eyebrow">Module under construction</p>
          <p class="ph__empty-text">
            该模块的功能将由其他工作单元接入。<br />
            页面骨架已就位 — 等待数据填充。
          </p>
        </div>
      </slot>
    </section>
  </article>
</template>

<style scoped>
.placeholder {
  padding: 18px 0 0;
  animation: ph-rise 0.5s ease both;
}
@keyframes ph-rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.ph__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 22px;
}
.ph__left { max-width: 720px; }
.ph__serial {
  text-transform: uppercase;
  letter-spacing: 0.16em;
  display: inline-block;
  margin-bottom: 12px;
}
.ph__title {
  font-family: var(--serif);
  font-weight: 300;
  font-size: clamp(34px, 4vw, 54px);
  letter-spacing: -0.02em;
  line-height: 1.05;
  margin: 0 0 14px;
  color: var(--ink);
  display: flex;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
}
.ph__title em {
  font-style: italic;
  color: var(--stamp);
  font-size: 0.6em;
}
.ph__caption {
  font-size: 15px;
  color: var(--mute);
  line-height: 1.6;
}

.ph__rule {
  height: 1px;
  background: var(--rule);
}

.ph__body { padding: 28px 0 60px; }
.ph__empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 14px;
  padding: 56px 0;
  max-width: 480px;
}
.ph__empty-mark .stamp {
  width: 56px; height: 56px;
  font-size: 24px;
}
.ph__empty-text {
  font-size: 14px;
  color: var(--mute);
  line-height: 1.7;
}
</style>
