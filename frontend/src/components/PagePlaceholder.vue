<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = withDefaults(
  defineProps<{
    title: string
    caption?: string
    /** Kept for backward compatibility, no longer rendered. */
    serial?: string
    subtitle?: string
  }>(),
  {
    caption: '本节即将上线，数据正在归档之中。',
    serial: '',
    subtitle: '',
  },
)

const route = useRoute()
const titleStr = computed(() => props.title || (route.meta?.title as string) || '—')
</script>

<template>
  <el-card shadow="never" class="placeholder">
    <template #header>
      <div class="placeholder__head">
        <span class="placeholder__title">{{ titleStr }}</span>
        <slot name="actions" />
      </div>
    </template>

    <slot>
      <el-empty description="模块开发中">
        <template #description>
          <div class="placeholder__caption">{{ caption }}</div>
        </template>
      </el-empty>
    </slot>
  </el-card>
</template>

<style scoped>
.placeholder {
  border-radius: 4px;
}

.placeholder__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.placeholder__title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.placeholder__caption {
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}
</style>
