import axios from 'axios'

export function analyzeResume(payload) {
  return axios.post('/api/analyze', payload)
}

/**
 * SSE streaming analyze — returns an async generator that yields
 * {event, data} objects for each server event.
 *
 * Events:
 *   step  — agent progress update
 *   result — final AnalysisResponse
 *   error  — error occurred
 */
export async function* analyzeResumeStream(payload) {
  const resp = await fetch('/api/analyze/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(detail.detail || `HTTP ${resp.status}`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // Keep last incomplete line in buffer
      buffer = lines.pop() || ''

      let dataLines = ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          dataLines += line.slice(6)
        } else if (line === '' && dataLines) {
          try {
            const parsed = JSON.parse(dataLines)
            if (parsed.event && parsed.data) {
              yield { event: parsed.event, data: parsed.data }
            }
          } catch {
            // skip malformed frames
          }
          dataLines = ''
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
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
