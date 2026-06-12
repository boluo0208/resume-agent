<template>
  <main class="page-shell">
    <section class="workspace">
      <aside class="input-panel">
        <div class="title-row">
          <div>
            <p class="eyebrow">Multi-Agent MVP</p>
            <h1>简历分析 Agent</h1>
          </div>
          <div class="status-tags">
            <el-tag type="success" effect="plain">FastAPI + Vue</el-tag>
            <el-tag :type="llmStatus.enabled ? 'primary' : 'info'" effect="plain">
              {{ llmStatus.enabled ? `LLM: ${llmStatus.model}` : 'Mock 模式' }}
            </el-tag>
          </div>
        </div>

        <el-form label-position="top">
          <el-form-item label="目标岗位">
            <el-input v-model="form.target_role" placeholder="例如：Python 后端开发工程师" />
          </el-form-item>

          <el-form-item label="简历内容">
            <div class="upload-row">
              <input
                ref="fileInput"
                type="file"
                accept=".pdf,.docx"
                style="display:none"
                @change="handleFileChange"
              />
              <el-button :loading="uploading" :disabled="uploading" @click="fileInput?.click()">
                📎 上传 PDF / DOCX
              </el-button>
              <span v-if="uploadFile" class="file-tag">
                {{ uploadFile.name }}
                <el-button size="small" circle plain @click="handleClearFile">✕</el-button>
              </span>
            </div>
            <el-input
              v-model="form.resume_text"
              type="textarea"
              :rows="12"
              resize="none"
              placeholder="把你的简历内容粘贴到这里，或上传 PDF / DOCX 文件自动提取"
            />
          </el-form-item>

          <el-form-item label="岗位 JD">
            <div class="upload-row">
              <input
                ref="jdFileInput"
                type="file"
                accept=".png,.jpg,.jpeg,.webp"
                style="display:none"
                @change="handleJdImageChange"
              />
              <el-button :loading="uploadingJd" :disabled="uploadingJd" @click="jdFileInput?.click()">
                📷 上传 JD 截图
              </el-button>
              <span v-if="uploadJdFile" class="file-tag">
                {{ uploadJdFile.name }}
                <el-button size="small" circle plain @click="handleClearJdImage">✕</el-button>
              </span>
            </div>
            <el-input
              v-model="form.jd_text"
              type="textarea"
              :rows="8"
              resize="none"
              placeholder="把招聘要求粘贴到这里，也可以直接 Ctrl+V 粘贴 JD 截图自动提取"
              @paste.capture="handleJdPaste"
            />
          </el-form-item>

          <el-button class="run-button" type="primary" size="large" :loading="loading" @click="handleAnalyze">
            运行多 Agent 分析
          </el-button>
        </el-form>
      </aside>

      <section class="report-panel">
        <div v-if="!result" class="empty-state">
          <h2>多 Agent 工作台</h2>
          <p>当前工作流：简历解析 Agent → JD 匹配 Agent → 简历诊断 Agent → 简历润色 Agent。配置大模型 Key 后，每个 Agent 会分别调用模型并返回结构化 JSON。</p>
        </div>

        <div v-else class="report-content">
          <div class="score-strip">
            <el-progress type="dashboard" :percentage="result.score" :width="132" />
            <div>
              <p class="eyebrow">Analysis Report / {{ result.mode === 'llm' ? result.model : 'mock' }}</p>
              <h2>{{ result.summary }}</h2>
            </div>
          </div>

          <section class="workflow-block">
            <h3>Agent 工作流</h3>
            <div class="agent-steps">
              <article v-for="step in result.agent_steps" :key="step.name" class="agent-step">
                <div class="step-dot"></div>
                <div>
                  <strong>{{ step.name }}</strong>
                  <p>{{ step.role }}</p>
                  <span>{{ step.summary }}</span>
                </div>
              </article>
            </div>
          </section>

          <section v-if="result.match_result" class="match-strip">
            <div>
              <p class="eyebrow">JD Match</p>
              <h3>{{ result.match_result.target_role }}：{{ result.match_result.match_score }}%</h3>
            </div>
            <div class="tag-groups">
              <div>
                <span class="tag-title">已命中</span>
                <el-tag v-for="item in result.match_result.matched_keywords" :key="item" type="success" effect="plain">{{ item }}</el-tag>
              </div>
              <div>
                <span class="tag-title">待补充</span>
                <el-tag v-for="item in result.match_result.missing_keywords" :key="item" type="warning" effect="plain">{{ item }}</el-tag>
              </div>
            </div>
          </section>

          <div class="report-grid">
            <section class="report-block">
              <h3>优势</h3>
              <ul>
                <li v-for="item in result.strengths" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="report-block warning">
              <h3>问题</h3>
              <ul>
                <li v-for="item in result.problems" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="report-block full">
              <h3>优化建议</h3>
              <ul>
                <li v-for="item in result.suggestions" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="report-block full optimized">
              <h3>优化后的简历表达</h3>
              <p>{{ result.optimized_resume }}</p>
            </section>

            <section class="report-block full interview">
              <h3>面试亮点</h3>
              <ul>
                <li v-for="item in result.interview_highlights" :key="item">{{ item }}</li>
              </ul>
            </section>
          </div>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { analyzeResume, getLlmStatus, parseResumeFile, parseJdImage } from '../api'

const loading = ref(false)
const uploading = ref(false)
const uploadFile = ref(null)
const fileInput = ref(null)

const uploadingJd = ref(false)
const uploadJdFile = ref(null)
const jdFileInput = ref(null)
const result = ref(null)
const llmStatus = reactive({ enabled: false, mode: 'mock', model: null })
const form = reactive({
  target_role: 'Python 后端开发工程师',
  resume_text: '',
  jd_text: ''
})

onMounted(async () => {
  try {
    const { data } = await getLlmStatus()
    Object.assign(llmStatus, data)
  } catch (error) {
    console.warn('LLM status check failed', error)
  }
})

const handleFileChange = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  uploadFile.value = file
  uploading.value = true

  try {
    const { data } = await parseResumeFile(file)
    form.resume_text = data.resume_text
    ElMessage.success(`已提取 ${data.char_count} 个字符，文本已填入下方文本框，可编辑后再分析`)
  } catch (error) {
    console.error(error)
    const detail = error.response?.data?.detail || '文件解析失败，请检查文件是否损坏或尝试手动粘贴'
    ElMessage.error(detail)
    uploadFile.value = null
  } finally {
    uploading.value = false
  }
}

const handleClearFile = () => {
  uploadFile.value = null
  form.resume_text = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleJdImageChange = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  await processJdImageFile(file)
  if (jdFileInput.value) {
    jdFileInput.value.value = ''
  }
}

const processJdImageFile = async (file) => {
  uploadJdFile.value = file
  uploadingJd.value = true

  try {
    const { data } = await parseJdImage(file)
    form.jd_text = data.text
    ElMessage.success(`已从图片提取 ${data.char_count} 个字符，文本已填入下方文本框，可编辑后再分析`)
  } catch (error) {
    console.error(error)
    const detail = error.response?.data?.detail || '图片解析失败，请检查图片是否清晰或尝试手动粘贴'
    ElMessage.error(detail)
    uploadJdFile.value = null
  } finally {
    uploadingJd.value = false
  }
}

const handleJdPaste = async (event) => {
  const items = Array.from(event.clipboardData?.items || [])
  const imageItem = items.find((item) => item.type.startsWith('image/'))
  if (!imageItem) return

  const file = imageItem.getAsFile()
  if (!file) return

  event.preventDefault()
  const ext = file.type.split('/')[1] || 'png'
  const pastedFile = new File([file], `pasted-jd-${Date.now()}.${ext}`, { type: file.type })
  await processJdImageFile(pastedFile)
}

const handleClearJdImage = () => {
  uploadJdFile.value = null
  form.jd_text = ''
  if (jdFileInput.value) {
    jdFileInput.value.value = ''
  }
}

const handleAnalyze = async () => {
  if (form.resume_text.trim().length < 10) {
    ElMessage.warning('先粘贴一段简历内容')
    return
  }

  loading.value = true
  try {
    const { data } = await analyzeResume({ ...form })
    result.value = data
  } catch (error) {
    console.error(error)
    ElMessage.error(error.response?.data?.detail || '分析失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.file-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #f0faf4;
  border: 1px solid #bfe6cf;
  border-radius: 6px;
  font-size: 13px;
  color: #25693d;
}
</style>
