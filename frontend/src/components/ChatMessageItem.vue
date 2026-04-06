<template>
  <div class="msg-item" :class="msg.role">
    <div class="role-label">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
    <div v-if="msg.role === 'user'" class="msg-content user-text">{{ msg.content }}</div>
    <div v-else class="msg-content" v-html="rendered"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '../utils/markdown'
import type { Message } from '../api'

const props = defineProps<{ msg: Message }>()

const rendered = computed(() => renderMarkdown(props.msg.content))
</script>

<style scoped>
.msg-item {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #313244;
}
.msg-item.user { background: #1e1e2e; }
.msg-item.assistant { background: #181825; }
.role-label {
  min-width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.msg-item.user .role-label { background: #89b4fa; color: #1e1e2e; }
.msg-item.assistant .role-label { background: #a6e3a1; color: #1e1e2e; }
.msg-content {
  flex: 1;
  line-height: 1.7;
  font-size: 14px;
  color: #cdd6f4;
  overflow-x: auto;
}
.msg-content :deep(pre.hljs) {
  background: #11111b;
  border-radius: 6px;
  padding: 12px 16px;
  overflow-x: auto;
  font-size: 13px;
}
.msg-content :deep(code) {
  font-family: 'Consolas', 'Courier New', monospace;
}
.msg-content :deep(p) { margin: 6px 0; }
.msg-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.msg-content :deep(th),
.msg-content :deep(td) {
  padding: 6px;
  border: 1px solid #313244;
  vertical-align: top;
}
.msg-content :deep(td img) {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 6px;
}
.user-text { white-space: pre-wrap; }
</style>
