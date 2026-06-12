<template>
  <main class="page-shell">
    <div class="workspace">
      <!-- ========== Left: Input Panel ========== -->
      <aside class="input-panel stagger-2">
        <div class="title-row">
          <div>
            <p class="eyebrow">Input</p>
            <h1>新建分析</h1>
          </div>
          <div class="status-tags">
            <el-tag size="small" effect="plain" round>FastAPI + Vue</el-tag>
            <el-tag
              size="small"
              :type="llmStatus.enabled ? 'warning' : 'info'"
              effect="plain"
              round
            >
              {{ llmStatus.enabled ? `LLM · ${llmStatus.model}` : 'Mock 模式' }}
            </el-tag>
          </div>
        </div>

        <el-form label-position="top">
          <el-form-item>
            <template #label>
              <span class="form-label-custom">目标岗位（可选）</span>
            </template>
            <el-input
              v-model="form.target_role"
              placeholder="可留空，系统会优先根据岗位 JD 自动识别"
              size="large"
            />
          </el-form-item>

          <el-form-item>
            <template #label>
              <span class="form-label-custom">简历内容</span>
            </template>
            <div class="upload-row">
              <input
                ref="fileInput"
                type="file"
                accept=".pdf,.docx"
                style="display:none"
                @change="handleFileChange"
              />
              <el-button
                :loading="uploading"
                :disabled="uploading"
                @click="fileInput?.click()"
                size="small"
                round
              >
                <span class="btn-icon">📎</span> 上传 PDF / DOCX
              </el-button>
              <span v-if="uploadFile" class="file-tag">
                {{ uploadFile.name }}
                <el-button size="small" circle plain @click="handleClearFile" class="clear-btn">✕</el-button>
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

          <el-form-item>
            <template #label>
              <span class="form-label-custom">岗位 JD</span>
            </template>
            <div class="upload-row">
              <input
                ref="jdFileInput"
                type="file"
                accept=".png,.jpg,.jpeg,.webp"
                style="display:none"
                @change="handleJdImageChange"
              />
              <el-button
                :loading="uploadingJd"
                :disabled="uploadingJd"
                @click="jdFileInput?.click()"
                size="small"
                round
              >
                <span class="btn-icon">📷</span> 上传 JD 截图
              </el-button>
              <span v-if="uploadJdFile" class="file-tag">
                {{ uploadJdFile.name }}
                <el-button size="small" circle plain @click="handleClearJdImage" class="clear-btn">✕</el-button>
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

          <el-button
            class="run-button"
            type="primary"
            size="large"
            :loading="loading"
            @click="handleAnalyze"
          >
            {{ loading ? 'Agent 分析中…' : '生成投递优化方案' }}
          </el-button>
        </el-form>
      </aside>

      <!-- ========== Right: Report Panel ========== -->
      <section class="report-panel stagger-3">
        <!-- Empty state -->
        <div v-if="!result" class="empty-state">
          <div class="empty-icon">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <rect x="8" y="8" width="48" height="48" rx="8" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
              <path d="M22 28h20M22 36h14M22 44h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" opacity="0.4"/>
            </svg>
          </div>
          <h2>多 Agent 工作台</h2>
          <p>
            当前工作流：优先根据 <strong>岗位 JD</strong> 自动识别目标岗位，再结合
            <strong>简历解析 Agent</strong> → <strong>JD 匹配 Agent</strong> →
            <strong>简历诊断 Agent</strong> → <strong>简历润色 Agent</strong>。
            <br />上方目标岗位可留空，也可作为你的求职方向补充参考。
          </p>
        </div>

        <!-- Report content -->
        <div v-else class="report-content">
          <!-- Score header -->
          <div class="score-strip stagger-1">
            <div class="score-ring">
              <svg class="score-ring-svg" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="52" fill="none" stroke="var(--color-border)" stroke-width="6" />
                <circle
                  class="score-ring-fill"
                  cx="60" cy="60" r="52"
                  fill="none"
                  stroke="var(--color-gold)"
                  stroke-width="6"
                  stroke-linecap="round"
                  :stroke-dasharray="339.292"
                  :stroke-dashoffset="339.292 - (339.292 * result.score / 100)"
                  transform="rotate(-90 60 60)"
                />
              </svg>
              <span class="score-value">{{ result.score }}</span>
            </div>
            <div>
              <p class="eyebrow">
                Analysis Report
                <span class="mode-badge">{{ result.mode === 'llm' ? result.model : 'mock' }}</span>
              </p>
              <h2>{{ result.summary }}</h2>
            </div>
          </div>

          <!-- Agent workflow -->
          <section class="workflow-block stagger-2">
            <h3>Agent 工作流</h3>
            <div class="agent-steps">
              <article
                v-for="(step, idx) in result.agent_steps"
                :key="step.name"
                class="agent-step"
                :style="{ animationDelay: `${0.08 * idx}s` }"
              >
                <div class="step-dot"></div>
                <strong>{{ step.name }}</strong>
                <p>{{ step.role }}</p>
                <span>{{ step.summary }}</span>
              </article>
            </div>
          </section>

          <!-- JD Match -->
          <section v-if="result.match_result" class="match-strip stagger-3">
            <div>
              <p class="eyebrow">JD Match</p>
              <h3>{{ result.match_result.target_role }}</h3>
              <div class="match-score-large">{{ result.match_result.match_score }}<span>%</span></div>
            </div>
            <div class="tag-groups">
              <div>
                <span class="tag-title">已命中</span>
                <el-tag
                  v-for="item in result.match_result.matched_keywords"
                  :key="item"
                  type="success"
                  effect="plain"
                  size="small"
                  round
                >{{ item }}</el-tag>
              </div>
              <div>
                <span class="tag-title">待补充</span>
                <el-tag
                  v-for="item in result.match_result.missing_keywords"
                  :key="item"
                  type="warning"
                  effect="plain"
                  size="small"
                  round
                >{{ item }}</el-tag>
              </div>
            </div>
          </section>

          <!-- Report grid -->
          <div class="report-grid">
            <section class="report-block stagger-4">
              <h3>优势</h3>
              <ul>
                <li v-for="item in result.strengths" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="report-block warning stagger-4">
              <h3>问题</h3>
              <ul>
                <li v-for="item in result.problems" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="report-block full optimized stagger-5">
              <h3>优化建议</h3>
              <ul>
                <li v-for="item in result.suggestions" :key="item">{{ item }}</li>
              </ul>
            </section>

            <section class="report-block full optimized stagger-6">
              <h3>优化后的简历表达</h3>
              <p>{{ result.optimized_resume }}</p>
            </section>

            <section class="report-block full interview stagger-7">
              <h3>面试亮点</h3>
              <ul>
                <li v-for="item in result.interview_highlights" :key="item">{{ item }}</li>
              </ul>
            </section>
          </div>
        </div>
      </section>
    </div>
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
  target_role: '',
  resume_text: '',
  jd_text: '',
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
  if (fileInput.value) fileInput.value.value = ''
}

const handleJdImageChange = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  await processJdImageFile(file)
  if (jdFileInput.value) jdFileInput.value.value = ''
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
  if (jdFileInput.value) jdFileInput.value.value = ''
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
/* ---- Custom form label ---- */
.form-label-custom {
  font-family: var(--font-body);
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--color-text-dim);
}

/* ---- Upload row ---- */
.upload-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.btn-icon {
  font-style: normal;
  margin-right: 2px;
}

.file-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 12px;
  background: rgba(106,158,133,0.1);
  border: 1px solid rgba(106,158,133,0.25);
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
  color: var(--color-sage);
}

.clear-btn {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: rgba(196,122,107,0.15);
  --el-button-hover-border-color: rgba(196,122,107,0.3);
  --el-button-text-color: var(--color-text-dim);
  font-size: 0.65rem;
  width: 18px;
  height: 18px;
  min-width: 18px;
  padding: 0;
}

/* ---- Empty state icon ---- */
.empty-icon {
  color: var(--color-text-dim);
  margin-bottom: var(--space-lg);
  opacity: 0.5;
}

/* ---- Score ring ---- */
.score-ring {
  position: relative;
  width: 120px;
  height: 120px;
  flex-shrink: 0;
}

.score-ring-svg {
  width: 100%;
  height: 100%;
}

.score-ring-fill {
  transition: stroke-dashoffset 1.2s var(--ease-out-expo);
}

.score-value {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 900;
  color: var(--color-gold);
}

/* ---- Mode badge ---- */
.mode-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 1px 8px;
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  background: rgba(212,168,83,0.12);
  border: 1px solid rgba(212,168,83,0.25);
  border-radius: 3px;
  color: var(--color-gold);
  text-transform: none;
  vertical-align: middle;
}

/* ---- Match score large ---- */
.match-score-large {
  font-family: var(--font-display);
  font-size: 2.8rem;
  font-weight: 900;
  color: var(--color-gold);
  line-height: 1;
  margin-top: var(--space-sm);
}

.match-score-large span {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--color-gold-dim);
}

/* ---- Agent step staggered ---- */
.agent-step {
  animation: fade-up 0.5s var(--ease-out-expo) both;
}
</style>
