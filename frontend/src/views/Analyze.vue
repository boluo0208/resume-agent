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
              <input ref="fileInput" type="file" accept=".pdf,.docx" style="display:none" @change="handleFileChange" />
              <el-button :loading="uploading" :disabled="uploading" @click="fileInput?.click()" size="small" round>
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
              <input ref="jdFileInput" type="file" accept=".png,.jpg,.jpeg,.webp" style="display:none" @change="handleJdImageChange" />
              <el-button :loading="uploadingJd" :disabled="uploadingJd" @click="jdFileInput?.click()" size="small" round>
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

        <!-- ═══ Empty state ═══ -->
        <div v-if="!loading && !result && !error" class="empty-state">
          <div class="empty-header">
            <h2>AI 投递优化工作台</h2>
            <p>上传简历和岗位 JD，系统会自动识别岗位、分析匹配度并生成优化建议。</p>
          </div>

          <!-- Horizontal pipeline -->
          <div class="pipeline">
            <div class="pipeline-track">
              <div
                v-for="(node, idx) in PIPELINE_NODES"
                :key="node.key"
                class="pipeline-node"
                :style="{ animationDelay: `${0.08 * idx}s` }"
              >
                <span class="node-num">{{ idx + 1 }}</span>
                <div class="node-text">
                  <strong>{{ node.title }}</strong>
                  <span>{{ node.desc }}</span>
                </div>
              </div>
            </div>
            <div class="pipeline-connectors">
              <span v-for="i in PIPELINE_NODES.length - 1" :key="i" class="pipe-arrow">
                <svg width="20" height="20" viewBox="0 0 20 20"><path d="M8 6l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </span>
            </div>
          </div>

          <!-- Status card -->
          <div class="status-card">
            <div class="status-card-top">
              <span class="status-badge">
                <span class="badge-dot"></span>
                等待开始
              </span>
              <span class="status-card-hint">请先上传简历并粘贴岗位 JD</span>
            </div>
            <div class="capability-tags">
              <span class="cap-tag">岗位识别</span>
              <span class="cap-tag">匹配评分</span>
              <span class="cap-tag">定向改写</span>
            </div>
          </div>
        </div>

        <!-- ═══ Progress state (SSE real-time) ═══ -->
        <div v-if="loading" class="progress-panel">
          <div class="progress-header">
            <p class="eyebrow">Agent 工作流执行中</p>
            <h2>AI 投递优化工作台</h2>
          </div>

          <!-- Pipeline with live status -->
          <div class="pipeline pipeline-live">
            <div class="pipeline-track">
              <div
                v-for="agent in progressAgents"
                :key="agent.key"
                class="pipeline-node"
                :class="'pn-' + agent.status"
              >
                <span class="node-num">
                  <span v-if="agent.status === 'completed'" class="num-check">
                    <svg viewBox="0 0 12 12"><path d="M2.5 6l2.5 2.5L9.5 3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  </span>
                  <span v-else-if="agent.status === 'running'" class="num-spin"></span>
                  <span v-else>{{ getAgentIndex(agent.key) + 1 }}</span>
                </span>
                <div class="node-text">
                  <strong>{{ getAgentTitle(agent.key) }}</strong>
                  <span>{{ agent.status === 'running' ? '执行中…' : agent.status === 'completed' ? '已完成' : '等待中' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Overall progress bar -->
          <div class="progress-bar-wrap">
            <div class="progress-bar-track">
              <div class="progress-bar-fill" :style="{ width: progressPercent + '%' }"></div>
            </div>
            <span class="progress-percent">{{ progressPercent }}%</span>
          </div>

          <!-- Current agent detail -->
          <div class="current-agent-card" v-if="currentRunningAgent">
            <span class="current-label">当前执行</span>
            <span class="current-name">{{ getAgentTitle(currentRunningAgent.key) }}</span>
            <span class="current-desc">{{ currentRunningAgent.label }}</span>
          </div>
        </div>

        <!-- ═══ Error state ═══ -->
        <div v-if="!loading && error" class="error-panel">
          <div class="error-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
              <path d="M24 15v12M24 33v-2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <h3>分析未完成</h3>
          <p>{{ error }}</p>
          <el-button round plain @click="handleRetry">重新分析</el-button>
        </div>

        <!-- ═══ Report content ═══ -->
        <div v-if="!loading && result && !error" class="report-content">
          <div class="score-strip stagger-1">
            <div class="score-ring">
              <svg class="score-ring-svg" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="52" fill="none" stroke="var(--color-border)" stroke-width="6" />
                <circle class="score-ring-fill" cx="60" cy="60" r="52" fill="none" stroke="var(--color-gold)" stroke-width="6" stroke-linecap="round"
                  :stroke-dasharray="339.292"
                  :stroke-dashoffset="339.292 - (339.292 * result.score / 100)"
                  transform="rotate(-90 60 60)" />
              </svg>
              <span class="score-value">{{ result.score }}</span>
            </div>
            <div>
              <p class="eyebrow">Analysis Report<span class="mode-badge">{{ result.mode === 'llm' ? result.model : 'mock' }}</span></p>
              <h2>{{ result.summary }}</h2>
            </div>
          </div>

          <section class="workflow-block stagger-2">
            <h3>Agent 工作流</h3>
            <div class="agent-steps">
              <article v-for="(step, idx) in result.agent_steps" :key="step.name" class="agent-step" :style="{ animationDelay: `${0.08 * idx}s` }">
                <div class="step-dot"></div>
                <strong>{{ step.name }}</strong>
                <p>{{ step.role }}</p>
                <span>{{ step.summary }}</span>
              </article>
            </div>
          </section>

          <section v-if="result.jd_profile" class="jd-profile-block stagger-3">
            <h3>系统识别岗位</h3>
            <div class="jd-profile-body">
              <div class="jd-profile-main">
                <span class="jd-role">{{ result.jd_profile.target_role }}</span>
                <el-tag size="small" effect="plain" round type="warning">{{ result.jd_profile.job_type }}</el-tag>
              </div>
              <div class="jd-profile-tags" v-if="result.jd_profile.must_have?.length">
                <span class="tag-title">核心要求</span>
                <el-tag v-for="item in result.jd_profile.must_have" :key="item" size="small" effect="plain" round>{{ item }}</el-tag>
              </div>
              <div class="jd-profile-tags" v-if="result.jd_profile.nice_to_have?.length">
                <span class="tag-title">加分项</span>
                <el-tag v-for="item in result.jd_profile.nice_to_have" :key="item" size="small" effect="plain" round type="success">{{ item }}</el-tag>
              </div>
              <div class="jd-profile-tags" v-if="result.jd_profile.risk_items?.length">
                <span class="tag-title">风险项</span>
                <el-tag v-for="item in result.jd_profile.risk_items" :key="item" size="small" effect="plain" round type="danger">{{ item }}</el-tag>
              </div>
            </div>
          </section>

          <section v-if="result.match_result" class="match-strip stagger-3">
            <div>
              <p class="eyebrow">JD Match</p>
              <h3>{{ result.match_result.target_role }}</h3>
              <div class="match-score-large">{{ result.match_result.match_score }}<span>%</span></div>
              <div class="match-breakdown" v-if="result.match_result.match_breakdown && Object.keys(result.match_result.match_breakdown).length">
                <div class="breakdown-item" v-for="(val, key) in result.match_result.match_breakdown" :key="key">
                  <span class="breakdown-label">{{ key }}</span>
                  <span class="breakdown-bar-bg"><span class="breakdown-bar-fill" :style="{ width: val / maxBreakdownVal * 100 + '%' }"></span></span>
                  <span class="breakdown-val">{{ val }}</span>
                </div>
              </div>
            </div>
            <div class="tag-groups">
              <div>
                <span class="tag-title">已命中</span>
                <el-tag v-for="item in result.match_result.matched_keywords" :key="item" type="success" effect="plain" size="small" round>{{ item }}</el-tag>
              </div>
              <div>
                <span class="tag-title">待补充</span>
                <el-tag v-for="item in result.match_result.missing_keywords" :key="item" type="warning" effect="plain" size="small" round>{{ item }}</el-tag>
              </div>
              <div v-if="result.match_result.risk_items?.length">
                <span class="tag-title">风险提示</span>
                <el-tag v-for="item in result.match_result.risk_items" :key="item" type="danger" effect="plain" size="small" round>{{ item }}</el-tag>
              </div>
            </div>
          </section>

          <div class="report-grid">
            <section class="report-block stagger-4"><h3>优势</h3><ul><li v-for="item in result.strengths" :key="item">{{ item }}</li></ul></section>
            <section class="report-block warning stagger-4"><h3>问题</h3><ul><li v-for="item in result.problems" :key="item">{{ item }}</li></ul></section>
            <section class="report-block full optimized stagger-5"><h3>优化建议</h3><ul><li v-for="item in result.suggestions" :key="item">{{ item }}</li></ul></section>
            <section class="report-block full optimized stagger-6"><h3>优化后的简历表达</h3><p>{{ result.optimized_resume }}</p></section>
            <section class="report-block full interview stagger-7"><h3>面试亮点</h3><ul><li v-for="item in result.interview_highlights" :key="item">{{ item }}</li></ul></section>
          </div>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { analyzeResumeStream, getLlmStatus, parseResumeFile, parseJdImage } from '../api'

// ---- Pipeline definitions ----
const PIPELINE_NODES = [
  { key: 'JDParserAgent',      title: 'JD 解析',   desc: '识别岗位类型与核心要求' },
  { key: 'ResumeParserAgent',  title: '简历解析',   desc: '提取技能、项目与经历' },
  { key: 'JDMatchAgent',       title: '匹配评分',   desc: '计算岗位匹配度与缺口' },
  { key: 'ResumeReviewAgent',  title: '风险诊断',   desc: '诊断简历问题与投递风险' },
  { key: 'ResumeRewriteAgent', title: '简历改写',   desc: '生成优化表达与面试亮点' },
]

const AGENT_INFO = [
  { key: 'JDParserAgent',      name: 'JDParserAgent',      label: '解析岗位 JD，识别岗位类型与核心要求' },
  { key: 'ResumeParserAgent',  name: 'ResumeParserAgent',  label: '解析简历，提取技能、项目与经历' },
  { key: 'JDMatchAgent',       name: 'JDMatchAgent',       label: '计算岗位匹配度、命中项与缺口' },
  { key: 'ResumeReviewAgent',  name: 'ResumeReviewAgent',  label: '诊断简历问题与投递风险' },
  { key: 'ResumeRewriteAgent', name: 'ResumeRewriteAgent', label: '生成优化表达与面试亮点' },
]

function getAgentIndex(key) {
  return PIPELINE_NODES.findIndex(n => n.key === key)
}

function getAgentTitle(key) {
  const node = PIPELINE_NODES.find(n => n.key === key)
  return node ? node.title : key
}

// ---- State ----
const loading = ref(false)
const error = ref(null)
const result = ref(null)

const uploading = ref(false)
const uploadFile = ref(null)
const fileInput = ref(null)

const uploadingJd = ref(false)
const uploadJdFile = ref(null)
const jdFileInput = ref(null)

const llmStatus = reactive({ enabled: false, mode: 'mock', model: null })

const progressPercent = ref(0)
const progressAgents = ref(
  AGENT_INFO.map((a) => ({ ...a, status: 'waiting' }))
)

const currentRunningAgent = computed(() =>
  progressAgents.value.find(a => a.status === 'running') || null
)

const maxBreakdownVal = computed(() => {
  if (!result.value?.match_result?.match_breakdown) return 40
  const vals = Object.values(result.value.match_result.match_breakdown)
  return Math.max(...vals, 1)
})

const form = reactive({
  target_role: '',
  resume_text: '',
  jd_text: '',
})

onMounted(async () => {
  try {
    const { data } = await getLlmStatus()
    Object.assign(llmStatus, data)
  } catch (err) {
    console.warn('LLM status check failed', err)
  }
})

function _resetProgress() {
  progressPercent.value = 0
  progressAgents.value = AGENT_INFO.map((a) => ({ ...a, status: 'waiting' }))
}

function _updateStep(key, status, progress, summary) {
  const agent = progressAgents.value.find((a) => a.key === key)
  if (agent) {
    agent.status = status
    if (summary) agent.label = summary
  }
  if (typeof progress === 'number') {
    progressPercent.value = Math.max(progressPercent.value, progress)
  }
}

const handleFileChange = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  uploadFile.value = file
  uploading.value = true
  try {
    const { data } = await parseResumeFile(file)
    form.resume_text = data.resume_text
    ElMessage.success(`已提取 ${data.char_count} 个字符，文本已填入下方文本框，可编辑后再分析`)
  } catch (err) {
    console.error(err)
    const detail = err.response?.data?.detail || '文件解析失败'
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
    ElMessage.success(`已从图片提取 ${data.char_count} 个字符`)
  } catch (err) {
    console.error(err)
    const detail = err.response?.data?.detail || '图片解析失败'
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
  error.value = null
  result.value = null
  loading.value = true
  _resetProgress()
  try {
    const stream = analyzeResumeStream({ ...form })
    for await (const { event, data } of stream) {
      if (event === 'step') {
        _updateStep(data.key, data.status, data.progress, data.summary)
      } else if (event === 'result') {
        progressPercent.value = 100
        progressAgents.value.forEach((a) => { a.status = 'completed' })
        result.value = data
      } else if (event === 'error') {
        error.value = data.message || '未知错误'
      }
    }
  } catch (err) {
    console.error(err)
    error.value = err.message || '分析失败，请检查后端服务是否正在运行'
  } finally {
    loading.value = false
  }
}

const handleRetry = () => {
  error.value = null
  result.value = null
  handleAnalyze()
}
</script>

<style scoped>
.form-label-custom {
  font-family: var(--font-body);
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--color-text-dim);
}

.upload-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.btn-icon { font-style: normal; margin-right: 2px; }

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

/* =============================================
   Empty state
   ============================================= */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 480px;
  gap: 0;
  text-align: center;
}

.empty-header {
  margin-bottom: var(--space-xl);
}

.empty-header h2 {
  font-size: 1.45rem;
  font-weight: 700;
  margin-bottom: var(--space-sm);
  color: var(--color-text);
}

.empty-header p {
  font-size: 0.88rem;
  color: var(--color-text-dim);
  max-width: 440px;
  line-height: 1.75;
  margin: 0 auto;
}

/* ---- Horizontal pipeline ---- */
.pipeline {
  position: relative;
  width: 100%;
  padding: 0 var(--space-md);
  margin-bottom: var(--space-xl);
}

.pipeline-track {
  display: flex;
  gap: var(--space-sm);
}

.pipeline-node {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-xs);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  text-align: center;
  animation: fade-up 0.45s var(--ease-out-expo) both;
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}

.pipeline-node:hover {
  border-color: var(--color-border-light);
}

.node-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-content: center;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--color-gold);
  background: rgba(139,105,20,0.07);
  border: 1px solid rgba(139,105,20,0.18);
  flex-shrink: 0;
  transition: all var(--duration-fast);
}

.node-text strong {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 2px;
  white-space: nowrap;
}

.node-text span {
  font-size: 0.66rem;
  color: var(--color-text-muted);
  line-height: 1.4;
}

/* ---- Status card ---- */
.status-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  padding: var(--space-lg);
  max-width: 420px;
  width: 100%;
  display: grid;
  gap: var(--space-md);
}

.status-card-top {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--color-text-dim);
  padding: 3px 12px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  white-space: nowrap;
}

.badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-text-muted);
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.45; }
  50%      { opacity: 1; }
}

.status-card-hint {
  font-size: 0.8rem;
  color: var(--color-text-dim);
}

.capability-tags {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.cap-tag {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--color-gold);
  padding: 3px 10px;
  border: 1px solid rgba(139,105,20,0.2);
  border-radius: var(--radius-sm);
  background: rgba(139,105,20,0.04);
}

/* =============================================
   Progress panel
   ============================================= */
.progress-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-xl) 0;
  gap: var(--space-lg);
}

.progress-header {
  text-align: center;
}

.progress-header h2 {
  margin-top: var(--space-xs);
  font-size: 1.45rem;
}

/* pipeline live states */
.pipeline-live .pipeline-node {
  transition: all var(--duration-base) var(--ease-out-expo);
}

.pipeline-live .pn-waiting {
  opacity: 0.4;
}

.pipeline-live .pn-running {
  border-color: var(--color-gold-dim);
  background: rgba(139,105,20,0.04);
  opacity: 1;
}

.pipeline-live .pn-running .node-num {
  border-color: var(--color-gold);
  background: rgba(139,105,20,0.12);
}

.pipeline-live .pn-completed .node-num {
  border-color: var(--color-sage);
  background: rgba(61,107,85,0.08);
  color: var(--color-sage);
}

.num-check {
  width: 14px;
  height: 14px;
  display: grid;
  place-content: center;
  color: var(--color-sage);
}

.num-spin {
  width: 14px;
  height: 14px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-gold);
  border-radius: 50%;
  display: block;
  animation: spin-rot 0.7s linear infinite;
}

@keyframes spin-rot {
  to { transform: rotate(360deg); }
}

.progress-bar-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  width: 100%;
  max-width: 500px;
}

.progress-bar-track {
  flex: 1;
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: var(--color-gold);
  border-radius: 2px;
  transition: width 0.4s var(--ease-out-expo);
}

.progress-percent {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-gold);
  min-width: 44px;
  text-align: right;
}

.current-agent-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px var(--space-md);
  align-items: center;
  max-width: 420px;
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  border: 1px solid var(--color-gold-dim);
  border-radius: var(--radius-md);
  background: rgba(139,105,20,0.03);
}

.current-label {
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-gold);
  grid-row: 1;
}

.current-name {
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--color-text);
  grid-row: 1;
  grid-column: 2;
}

.current-desc {
  font-size: 0.72rem;
  color: var(--color-text-dim);
  grid-column: 2;
}

/* =============================================
   Error panel
   ============================================= */
.error-panel {
  display: grid;
  place-content: center;
  justify-items: center;
  min-height: 400px;
  text-align: center;
  gap: var(--space-md);
}

.error-icon {
  color: var(--color-rose);
  margin-bottom: var(--space-sm);
  opacity: 0.6;
}

.error-panel h3 { color: var(--color-text); }

.error-panel p {
  max-width: 400px;
  color: var(--color-text-dim);
  font-size: 0.9rem;
  line-height: 1.7;
  margin: 0;
}

/* =============================================
   Report (existing)
   ============================================= */
.score-ring {
  position: relative;
  width: 120px;
  height: 120px;
  flex-shrink: 0;
}

.score-ring-svg { width: 100%; height: 100%; }

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

.agent-step {
  animation: fade-up 0.5s var(--ease-out-expo) both;
}

.jd-profile-block {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
  background: var(--color-surface);
}

.jd-profile-block h3 {
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.jd-profile-block h3::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-gold);
}

.jd-profile-body { display: grid; gap: var(--space-md); }

.jd-profile-main {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.jd-role {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-text);
}

.jd-profile-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px;
}

.jd-profile-tags .tag-title {
  min-width: 56px;
  font-size: 0.72rem;
}

.match-breakdown {
  margin-top: var(--space-md);
  display: grid;
  gap: 6px;
}

.breakdown-item {
  display: grid;
  grid-template-columns: 70px 1fr 32px;
  align-items: center;
  gap: var(--space-sm);
  font-size: 0.75rem;
}

.breakdown-label {
  color: var(--color-text-dim);
  font-weight: 600;
  text-align: right;
}

.breakdown-bar-bg {
  display: block;
  height: 6px;
  background: var(--color-border);
  border-radius: 3px;
  overflow: hidden;
}

.breakdown-bar-fill {
  display: block;
  height: 100%;
  background: var(--color-gold);
  border-radius: 3px;
  transition: width 0.8s var(--ease-out-expo);
}

.breakdown-val {
  color: var(--color-text);
  font-weight: 700;
  font-family: var(--font-display);
}

/* ---- Pipeline responsive ---- */
@media (max-width: 860px) {
  .pipeline-track {
    flex-wrap: wrap;
    justify-content: center;
  }

  .pipeline-node {
    flex: 1 1 100px;
    min-width: 80px;
  }
}

@media (max-width: 640px) {
  .empty-header h2 { font-size: 1.2rem; }
  .empty-header p { font-size: 0.82rem; }
}
</style>
