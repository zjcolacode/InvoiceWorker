<template>
  <el-dialog
    v-model="visible"
    title="上传发票"
    width="640px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="upload-form">
      <div class="form-row">
        <label class="form-label">来源类型</label>
        <el-radio-group v-model="sourceType" :disabled="uploading">
          <el-radio-button value="pdf">电子发票 (PDF)</el-radio-button>
          <el-radio-button value="paper">纸质发票 (照片)</el-radio-button>
        </el-radio-group>
      </div>

      <el-upload
        ref="uploadRef"
        class="invoice-upload"
        drag
        multiple
        :auto-upload="false"
        :accept="acceptTypes"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
        :disabled="uploading"
        @click="handleUploadClick"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击选择</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 {{ tipText }}，单文件不超过 20MB，可批量上传
          </div>
        </template>
      </el-upload>
    </div>

    <template #footer>
      <el-button @click="handleClose" :disabled="uploading">取消</el-button>
      <el-button
        type="primary"
        :loading="uploading"
        :disabled="fileList.length === 0"
        @click="handleSubmit"
      >
        开始上传 ({{ fileList.length }})
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage, type UploadFile, type UploadInstance, type UploadUserFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadInvoices } from '@/api/invoice'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'success'): void
}>()

const visible = ref(props.modelValue)
watch(
  () => props.modelValue,
  (val) => (visible.value = val),
)
watch(visible, (val) => emit('update:modelValue', val))

const sourceType = ref<'pdf' | 'paper'>('pdf')
const fileList = ref<UploadUserFile[]>([])
const uploading = ref(false)
const uploadRef = ref<UploadInstance>()

const acceptTypes = computed(() =>
  sourceType.value === 'pdf' ? '.pdf' : '.jpg,.jpeg,.png',
)
const tipText = computed(() =>
  sourceType.value === 'pdf' ? 'PDF' : 'JPG / JPEG / PNG',
)

const MAX_SIZE = 20 * 1024 * 1024

watch(sourceType, () => {
  // 切换源类型时清空已选
  fileList.value = []
  uploadRef.value?.clearFiles()
})

function handleFileChange(file: UploadFile, files: UploadUserFile[]) {
  // 大小校验
  if (file.size && file.size > MAX_SIZE) {
    ElMessage.error(`${file.name} 超过 20MB 限制`)
    fileList.value = files.filter((f) => f.uid !== file.uid)
    return
  }
  // 类型校验
  const name = (file.name || '').toLowerCase()
  const allowed = sourceType.value === 'pdf' ? ['.pdf'] : ['.jpg', '.jpeg', '.png']
  if (!allowed.some((ext) => name.endsWith(ext))) {
    ElMessage.error(`${file.name} 文件类型不符`)
    fileList.value = files.filter((f) => f.uid !== file.uid)
    return
  }
  fileList.value = files
}

function handleFileRemove(_file: UploadFile, files: UploadUserFile[]) {
  fileList.value = files
}

// 修复：原生文件选择器关闭后浏览器窗口焦点丢失，导致对话框按钮无法响应点击
// 在触发文件选择器后延迟调用 window.focus()，确保窗口恢复激活状态
function handleUploadClick() {
  // 延迟执行：文件选择器打开期间 JS 被阻塞，关闭后 setTimeout 回调立即触发
  // 给浏览器 300ms 完成文件选择器的关闭动画和内部清理
  setTimeout(() => {
    window.focus()
  }, 300)

  // 备用方案：监听 input[type=file] 的 cancel 事件（用户取消文件选择时触发）
  nextTick(() => {
    const input = uploadRef.value?.$el?.querySelector(
      'input[type=file]',
    ) as HTMLInputElement | null
    if (input && !input.dataset.focusBound) {
      input.dataset.focusBound = '1'
      input.addEventListener(
        'cancel',
        () => {
          setTimeout(() => window.focus(), 100)
        },
        { once: true },
      )
    }
  })
}

async function handleSubmit() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }
  const realFiles = fileList.value
    .map((f) => f.raw as File | undefined)
    .filter((f): f is File => !!f)

  if (realFiles.length === 0) {
    ElMessage.warning('未找到可上传的文件')
    return
  }

  uploading.value = true
  try {
    const res = await uploadInvoices(realFiles, sourceType.value)
    const uploadedCount = res?.uploaded?.length ?? 0
    const skipped = res?.skipped ?? []

    if (uploadedCount > 0 && skipped.length === 0) {
      ElMessage.success(res?.message || `成功上传 ${uploadedCount} 个文件`)
    } else if (uploadedCount > 0 && skipped.length > 0) {
      ElMessage.warning(
        `${res?.message || `成功上传 ${uploadedCount} 个文件，跳过 ${skipped.length} 个重复文件`}\n` +
          skipped.map((s) => `· ${s.filename}：${s.reason}`).join('\n'),
      )
    } else if (uploadedCount === 0 && skipped.length > 0) {
      ElMessage.warning(
        `所有文件均为重复文件，未上传。\n` +
          skipped.map((s) => `· ${s.filename}：${s.reason}`).join('\n'),
      )
    } else {
      ElMessage.info(res?.message || '未上传任何文件')
    }

    if (uploadedCount > 0) {
      emit('success')
    }
    handleClose()
  } catch (e) {
    // 错误已在拦截器中提示
    console.error(e)
  } finally {
    uploading.value = false
  }
}

function handleClose() {
  fileList.value = []
  uploadRef.value?.clearFiles()
  visible.value = false
}
</script>

<style scoped>
.upload-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.form-label {
  font-size: 14px;
  color: #606266;
  min-width: 72px;
}

.invoice-upload :deep(.el-upload-dragger) {
  padding: 32px 20px;
}
</style>
