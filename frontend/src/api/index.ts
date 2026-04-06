import axios from 'axios'

const qwenHttp = axios.create({
  baseURL: '/api/qwen',
  timeout: 120000,
})

const remotesamHttp = axios.create({
  baseURL: '/api/remotesam',
  timeout: 120000,
})

/* ---- 健康检查 ---- */
export const getHealth = () => qwenHttp.get('/health')
export const getRemoteSamHealth = () => remotesamHttp.get('/remotesam/health')

/* ---- 会话 ---- */
export interface Session {
  id: number
  title: string
  system_prompt: string | null
  created_at: string
  updated_at: string
  message_count?: number
}

export const getSessions = () => qwenHttp.get<Session[]>('/sessions')

export const createSession = (title: string, system_prompt?: string) =>
  qwenHttp.post<Session>('/sessions', { title, system_prompt })

export const deleteSession = (id: number) => qwenHttp.delete(`/sessions/${id}`)

/* ---- 消息 ---- */
export interface Message {
  id: number
  session_id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  sequence_no: number
  created_at: string
}

export const getMessages = (sessionId: number) =>
  qwenHttp.get<Message[]>(`/sessions/${sessionId}/messages`)

/* ---- 聊天 ---- */
export interface ChatRequest {
  session_id: number
  message: string
  temperature?: number
  top_p?: number
  max_new_tokens?: number
  stream?: boolean
}

export interface ChatResponse {
  session_id: number
  user_message_id: number
  assistant_message_id: number
  reply: string
}

export const sendChat = (payload: ChatRequest) =>
  qwenHttp.post<ChatResponse>('/chat', payload)

/**
 * 流式聊天：返回原生 fetch Response，调用方自行读取 SSE
 */
export async function sendChatStream(payload: ChatRequest): Promise<Response> {
  const resp = await fetch('/api/qwen/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!resp.ok) throw new Error(`Stream request failed: ${resp.status}`)
  return resp
}

export interface RemoteSamInferResponse {
  service: 'remotesam'
  task: 'referring_seg' | 'detection'
  question: string
  answer: string
  mask_png_base64?: string
  overlay_png_base64?: string
  boxes?: Record<string, Array<[number, number, number, number, number]>>
}

export async function sendRemoteSamInfer(payload: {
  image: File
  question: string
  task?: 'referring_seg' | 'detection'
  classnames?: string
}): Promise<RemoteSamInferResponse> {
  const form = new FormData()
  form.append('image', payload.image)
  form.append('question', payload.question)
  form.append('task', payload.task ?? 'referring_seg')
  form.append('classnames', payload.classnames ?? 'airplane,vehicle')

  const { data } = await remotesamHttp.post<RemoteSamInferResponse>('/remotesam/infer', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
  return data
}
