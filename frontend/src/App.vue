<template>
  <div class="app-layout">
    <SessionSidebar
      :sessions="sessions"
      :activeId="activeSessionId"
      @create="handleCreateSession"
      @select="handleSelectSession"
      @delete="handleDeleteSession"
    />
    <div class="chat-area">
      <!-- 顶部状态栏 -->
      <div class="topbar">
        <span v-if="activeSession">{{ activeSession.title }}</span>
        <span v-else>请选择或创建会话</span>
        <div class="topbar-right">
          <select v-model="serviceType" class="service-select">
            <option value="qwen">Qwen 文本后端</option>
            <option value="remotesam">RemoteSAM 多模态后端</option>
          </select>
          <span class="model-badge" :class="{ ok: qwenLoaded }">
            {{ qwenLoaded ? 'Qwen 已加载' : 'Qwen 未加载' }}
          </span>
          <span class="model-badge" :class="{ ok: remotesamLoaded, warm: !remotesamLoaded && remotesamReachable }">
            {{ remotesamLoaded ? 'RemoteSAM 已加载' : (remotesamReachable ? 'RemoteSAM 待加载(可用)' : 'RemoteSAM 不可用') }}
          </span>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="messages" ref="msgContainer">
        <div v-if="!activeSessionId" class="placeholder">
          <p>欢迎使用本地 AI 编码助手</p>
          <p>点击左侧「+ 新会话」开始提问</p>
          <div class="examples">
            <div class="example-item" v-for="q in exampleQuestions" :key="q" @click="handleExampleClick(q)">
              {{ q }}
            </div>
          </div>
        </div>
        <ChatMessageItem v-for="m in messages" :key="m.id" :msg="m" />
        <!-- 流式输出占位 -->
        <div v-if="streamContent" class="msg-item assistant">
          <div class="role-label" style="background:#a6e3a1;color:#1e1e2e;">AI</div>
          <div class="msg-content" v-html="streamRendered"></div>
        </div>
      </div>

      <!-- 输入框 -->
      <ChatInputBox :loading="loading" :service-type="serviceType" @send="handleSend" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import {
  getSessions, createSession, deleteSession,
  getMessages, sendChatStream, sendRemoteSamInfer, getHealth, getRemoteSamHealth,
  type Session, type Message,
} from './api'
import { renderMarkdown } from './utils/markdown'
import SessionSidebar from './components/SessionSidebar.vue'
import ChatMessageItem from './components/ChatMessageItem.vue'
import ChatInputBox from './components/ChatInputBox.vue'

const sessions = ref<Session[]>([])
const activeSessionId = ref<number | null>(null)
const messages = ref<Message[]>([])
const loading = ref(false)
const qwenLoaded = ref(false)
const remotesamLoaded = ref(false)
const remotesamReachable = ref(false)
const streamContent = ref('')
const msgContainer = ref<HTMLDivElement>()
const serviceType = ref<'qwen' | 'remotesam'>('qwen')
let statusTimer: number | undefined

const activeSession = computed(() =>
  sessions.value.find(s => s.id === activeSessionId.value) ?? null
)

const streamRendered = computed(() => renderMarkdown(streamContent.value))

const exampleQuestions = [
  '用 Python 写一个快速排序',
  '解释 JavaScript 的闭包',
  'FastAPI 如何实现流式响应',
  'Vue 3 的 ref 和 reactive 有什么区别',
]

/* ---- 初始化 ---- */
onMounted(async () => {
  await loadSessions()
  await refreshModelStatus()
  statusTimer = window.setInterval(refreshModelStatus, 10000)
})

onUnmounted(() => {
  if (statusTimer) {
    window.clearInterval(statusTimer)
  }
})

async function refreshModelStatus() {
  try {
    const { data } = await getHealth()
    qwenLoaded.value = !!data?.model_loaded
  } catch {
    qwenLoaded.value = false
  }

  try {
    const { data } = await getRemoteSamHealth()
    remotesamLoaded.value = !!data?.loaded
    remotesamReachable.value = true
  } catch {
    remotesamLoaded.value = false
    remotesamReachable.value = false
  }
}

async function loadSessions() {
  try {
    const { data } = await getSessions()
    sessions.value = data
  } catch { sessions.value = [] }
}

/* ---- 会话操作 ---- */
async function handleCreateSession() {
  const { data } = await createSession('新会话')
  sessions.value.unshift(data)
  await handleSelectSession(data.id)
}

async function handleSelectSession(id: number) {
  activeSessionId.value = id
  try {
    const { data } = await getMessages(id)
    messages.value = data
  } catch { messages.value = [] }
  await nextTick()
  scrollToBottom()
}

async function handleDeleteSession(id: number) {
  await deleteSession(id)
  sessions.value = sessions.value.filter(s => s.id !== id)
  if (activeSessionId.value === id) {
    activeSessionId.value = null
    messages.value = []
  }
}

/* ---- 发送消息（流式） ---- */
async function handleSend(payload: { text: string; imageFile: File | null }) {
  const text = payload.text
  if (!activeSessionId.value) {
    const { data } = await createSession(text.slice(0, 30))
    sessions.value.unshift(data)
    activeSessionId.value = data.id
  }

  if (serviceType.value === 'remotesam') {
    await handleSendRemoteSAM(payload)
    return
  }

  const userMsg: Message = {
    id: Date.now(),
    session_id: activeSessionId.value!,
    role: 'user',
    content: text,
    sequence_no: messages.value.length + 1,
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)
  await nextTick()
  scrollToBottom()

  loading.value = true
  streamContent.value = ''

  try {
    const resp = await sendChatStream({
      session_id: activeSessionId.value!,
      message: text,
      stream: true,
    })

    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop()!
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6).trim()
        if (payload === '[DONE]') continue
        try {
          const evt = JSON.parse(payload)
          if (evt.type === 'delta') {
            streamContent.value += evt.content
            await nextTick()
            scrollToBottom()
          } else if (evt.type === 'end') {
            const assistantMsg: Message = {
              id: evt.assistant_message_id ?? Date.now() + 1,
              session_id: activeSessionId.value!,
              role: 'assistant',
              content: streamContent.value,
              sequence_no: messages.value.length + 1,
              created_at: new Date().toISOString(),
            }
            messages.value.push(assistantMsg)
            streamContent.value = ''
          } else if (evt.type === 'error') {
            streamContent.value += `\n\n**错误**: ${evt.content}`
          }
        } catch { /* skip */ }
      }
    }

    if (streamContent.value) {
      messages.value.push({
        id: Date.now() + 2,
        session_id: activeSessionId.value!,
        role: 'assistant',
        content: streamContent.value,
        sequence_no: messages.value.length + 1,
        created_at: new Date().toISOString(),
      })
      streamContent.value = ''
    }
  } catch (err: any) {
    messages.value.push({
      id: Date.now() + 3,
      session_id: activeSessionId.value!,
      role: 'assistant',
      content: `**请求失败**: ${err.message || '未知错误'}`,
      sequence_no: messages.value.length + 1,
      created_at: new Date().toISOString(),
    })
  } finally {
    loading.value = false
    await refreshModelStatus()
    loadSessions()
    await nextTick()
    scrollToBottom()
  }
}

async function handleSendRemoteSAM(payload: { text: string; imageFile: File | null }) {
  const imageName = payload.imageFile?.name || '未上传图片'
  const userMsg: Message = {
    id: Date.now(),
    session_id: activeSessionId.value!,
    role: 'user',
    content: `${payload.text}\n\n[图片] ${imageName}`,
    sequence_no: messages.value.length + 1,
    created_at: new Date().toISOString(),
  }
  messages.value.push(userMsg)
  await nextTick()
  scrollToBottom()

  if (!payload.imageFile) {
    messages.value.push({
      id: Date.now() + 100,
      session_id: activeSessionId.value!,
      role: 'assistant',
      content: '**RemoteSAM 需要上传图片后再发送。**',
      sequence_no: messages.value.length + 1,
      created_at: new Date().toISOString(),
    })
    return
  }

  loading.value = true
  try {
    const result = await sendRemoteSamInfer({
      image: payload.imageFile,
      question: payload.text,
      task: 'referring_seg',
    })

    const mdParts = [
      `**服务**: RemoteSAM`,
      `**任务**: ${result.task}`,
      `**结果**: ${result.answer}`,
    ]

    if (result.overlay_png_base64 && result.mask_png_base64) {
      mdParts.push(
        '| overlay | mask |\n|---|---|\n' +
        `| ![overlay](data:image/png;base64,${result.overlay_png_base64}) | ![mask](data:image/png;base64,${result.mask_png_base64}) |`
      )
    } else {
      if (result.overlay_png_base64) {
        mdParts.push(`![overlay](data:image/png;base64,${result.overlay_png_base64})`)
      }
      if (result.mask_png_base64) {
        mdParts.push(`![mask](data:image/png;base64,${result.mask_png_base64})`)
      }
    }

    messages.value.push({
      id: Date.now() + 101,
      session_id: activeSessionId.value!,
      role: 'assistant',
      content: mdParts.join('\n\n'),
      sequence_no: messages.value.length + 1,
      created_at: new Date().toISOString(),
    })
    await refreshModelStatus()
  } catch (err: any) {
    messages.value.push({
      id: Date.now() + 102,
      session_id: activeSessionId.value!,
      role: 'assistant',
      content: `**RemoteSAM 请求失败**: ${err.message || '未知错误'}`,
      sequence_no: messages.value.length + 1,
      created_at: new Date().toISOString(),
    })
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

function handleExampleClick(q: string) {
  handleSend({ text: q, imageFile: null })
}

function scrollToBottom() {
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body, #app { height: 100%; }
body { font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; }
</style>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background: #11111b;
  color: #cdd6f4;
}
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background: #1e1e2e;
  border-bottom: 1px solid #313244;
  font-size: 14px;
}
.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.service-select {
  border: 1px solid #45475a;
  border-radius: 8px;
  background: #11111b;
  color: #cdd6f4;
  padding: 6px 10px;
  font-size: 12px;
}
.model-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: #45475a;
}
.model-badge.ok { background: #a6e3a1; color: #1e1e2e; }
.model-badge.warm { background: #f9e2af; color: #1e1e2e; }
.messages {
  flex: 1;
  overflow-y: auto;
}
.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: #6c7086;
}
.placeholder p { font-size: 16px; }
.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  max-width: 600px;
}
.example-item {
  padding: 8px 16px;
  background: #313244;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: background .15s;
}
.example-item:hover { background: #45475a; }
.msg-item {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #313244;
}
.msg-item.assistant { background: #181825; }
.role-label {
  min-width: 28px; height: 28px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; flex-shrink: 0;
}
.msg-content {
  flex: 1; line-height: 1.7; font-size: 14px; color: #cdd6f4; overflow-x: auto;
}
.msg-content :deep(pre.hljs) {
  background: #11111b; border-radius: 6px; padding: 12px 16px; overflow-x: auto; font-size: 13px;
}
.msg-content :deep(code) { font-family: 'Consolas', 'Courier New', monospace; }
</style>
