import axios from 'axios'

export function analyzeResume(payload) {
  return axios.post('/api/analyze', payload)
}

export function getLlmStatus() {
  return axios.get('/api/llm/status')
}

export async function parseResumeFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch('/api/resume/parse', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    return Promise.reject({ response: { status: res.status, data: detail } })
  }
  const data = await res.json()
  return { data }
}

export async function parseJdImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch('/api/resume/parse-image', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    return Promise.reject({ response: { status: res.status, data: detail } })
  }
  const data = await res.json()
  return { data }
}
