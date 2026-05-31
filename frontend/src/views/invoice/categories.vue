<template>
  <div class="categories-page">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button type="primary" :icon="Plus" @click="openCreate">
          新建分类
        </el-button>
        <el-button :icon="Refresh" @click="loadList">刷新</el-button>
      </div>
      <div class="toolbar-right">
        <el-button :icon="MagicStick" @click="handleInitDefaults" :loading="initLoading">
          初始化默认分类
        </el-button>
        <el-popconfirm
          title="将对所有未分类发票按照当前分类规则重新分类，确认继续？"
          confirm-button-text="确认"
          cancel-button-text="取消"
          @confirm="handleReclassify"
        >
          <template #reference>
            <el-button type="warning" :icon="Sort" :loading="reclassifyLoading">
              批量重新分类
            </el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <!-- 分类列表 -->
    <el-table
      v-loading="loading"
      :data="tableData"
      border
      stripe
      style="width: 100%"
      empty-text="暂无分类，可点击右上角『初始化默认分类』"
    >
      <el-table-column label="分类名称" min-width="180">
        <template #default="{ row }">
          <el-tag
            :color="row.color"
            effect="dark"
            :style="{ color: '#fff', borderColor: row.color }"
          >
            {{ row.name }}
          </el-tag>
          <el-tag v-if="!row.is_active" type="info" size="small" style="margin-left: 6px">
            已停用
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="关键词" min-width="320">
        <template #default="{ row }">
          <div class="keyword-list">
            <el-tag
              v-for="(kw, idx) in splitKeywords(row.keywords)"
              :key="idx"
              size="small"
              type="info"
              effect="plain"
              class="keyword-tag"
            >
              {{ kw }}
            </el-tag>
            <span v-if="splitKeywords(row.keywords).length === 0" class="placeholder">
              （未配置关键词，将作为兜底分类）
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="描述" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.description || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="颜色" width="100" align="center">
        <template #default="{ row }">
          <span class="color-swatch" :style="{ background: row.color }" />
          <span class="color-code">{{ row.color }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openEdit(row as Category)">
            编辑
          </el-button>
          <el-button
            type="warning"
            link
            size="small"
            @click="handleToggleActive(row as Category)"
          >
            {{ row.is_active ? '停用' : '启用' }}
          </el-button>
          <el-popconfirm
            title="确认删除该分类？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            @confirm="handleDelete(row as Category)"
          >
            <template #reference>
              <el-button type="danger" link size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑分类' : '新建分类'"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        label-position="right"
      >
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="例如：办公用品"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="颜色" prop="color">
          <el-color-picker v-model="form.color" show-alpha :predefine="presetColors" />
          <span class="color-code-inline">{{ form.color }}</span>
        </el-form-item>
        <el-form-item label="关键词" prop="keywords">
          <el-input
            v-model="form.keywords"
            type="textarea"
            :rows="4"
            placeholder="多个关键词用英文逗号分隔，例如：办公,文具,打印,复印"
          />
          <div class="form-hint">
            提示：识别完成后，系统会用发票的开票内容匹配关键词，命中数最高的分类作为结果。
          </div>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="可选，对该分类的简短说明"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editingId ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Plus, Refresh, MagicStick, Sort } from '@element-plus/icons-vue'
import {
  createCategory,
  deleteCategory,
  getCategories,
  initDefaults,
  reclassify,
  updateCategory,
  type Category,
  type CategoryCreatePayload,
} from '@/api/category'

const loading = ref(false)
const tableData = ref<Category[]>([])

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const initLoading = ref(false)
const reclassifyLoading = ref(false)

const form = reactive<CategoryCreatePayload>({
  name: '',
  keywords: '',
  description: '',
  color: '#409EFF',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入分类名称', trigger: 'blur' },
    { max: 100, message: '名称不超过100字', trigger: 'blur' },
  ],
  color: [{ required: true, message: '请选择颜色', trigger: 'change' }],
}

const presetColors = [
  '#409EFF',
  '#67C23A',
  '#E6A23C',
  '#F56C6C',
  '#909399',
  '#9B59B6',
  '#3498DB',
  '#BDC3C7',
  '#1ABC9C',
  '#34495E',
]

function splitKeywords(raw?: string | null): string[] {
  if (!raw) return []
  return raw
    .split(/[,，;；\s\r\n]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

async function loadList() {
  loading.value = true
  try {
    tableData.value = await getCategories()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.name = ''
  form.keywords = ''
  form.description = ''
  form.color = '#409EFF'
  editingId.value = null
  formRef.value?.clearValidate()
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(row: Category) {
  editingId.value = row.id
  form.name = row.name
  form.keywords = row.keywords || ''
  form.description = row.description || ''
  form.color = row.color || '#409EFF'
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingId.value) {
      await updateCategory(editingId.value, {
        name: form.name,
        keywords: form.keywords || null,
        description: form.description || null,
        color: form.color,
      })
      ElMessage.success('已保存')
    } else {
      await createCategory({
        name: form.name,
        keywords: form.keywords || null,
        description: form.description || null,
        color: form.color,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadList()
  } catch (e) {
    console.error(e)
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Category) {
  try {
    await deleteCategory(row.id)
    ElMessage.success(`已删除分类：${row.name}`)
    await loadList()
  } catch (e) {
    console.error(e)
  }
}

async function handleToggleActive(row: Category) {
  try {
    await updateCategory(row.id, { is_active: !row.is_active })
    ElMessage.success(row.is_active ? '已停用' : '已启用')
    await loadList()
  } catch (e) {
    console.error(e)
  }
}

async function handleInitDefaults() {
  initLoading.value = true
  try {
    const res = await initDefaults()
    if (res.created > 0) {
      ElMessage.success(`已新增 ${res.created} 个默认分类`)
    } else {
      ElMessage.info('默认分类已存在，无需重复创建')
    }
    await loadList()
  } catch (e) {
    console.error(e)
  } finally {
    initLoading.value = false
  }
}

async function handleReclassify() {
  reclassifyLoading.value = true
  try {
    const res = await reclassify()
    ElMessageBox.alert(
      `共处理 ${res.total} 条，更新 ${res.updated} 条，跳过 ${res.skipped} 条（无开票内容）。`,
      '批量分类完成',
      { type: 'success', confirmButtonText: '我知道了' },
    )
  } catch (e) {
    console.error(e)
  } finally {
    reclassifyLoading.value = false
  }
}

loadList()
</script>

<style scoped>
.categories-page {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.keyword-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 6px;
}

.keyword-tag {
  margin: 0;
}

.placeholder {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.color-swatch {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  vertical-align: middle;
  margin-right: 6px;
  border: 1px solid var(--el-border-color-lighter);
}

.color-code {
  font-family: monospace;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.color-code-inline {
  margin-left: 12px;
  font-family: monospace;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.form-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}
</style>
