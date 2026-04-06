<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h2>AI 编码助手</h2>
      <button class="btn-new" @click="$emit('create')">+ 新会话</button>
    </div>
    <div class="session-list">
      <div
        v-for="s in sessions"
        :key="s.id"
        class="session-item"
        :class="{ active: s.id === activeId }"
        @click="$emit('select', s.id)"
      >
        <span class="session-title">{{ s.title }}</span>
        <button class="btn-del" @click.stop="$emit('delete', s.id)" title="删除">&times;</button>
      </div>
      <div v-if="sessions.length === 0" class="empty">暂无会话</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Session } from '../api'

defineProps<{
  sessions: Session[]
  activeId: number | null
}>()

defineEmits<{
  (e: 'create'): void
  (e: 'select', id: number): void
  (e: 'delete', id: number): void
}>()
</script>

<style scoped>
.sidebar {
  width: 260px;
  min-width: 260px;
  background: #1e1e2e;
  color: #cdd6f4;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #313244;
}
.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #313244;
}
.sidebar-header h2 {
  margin: 0 0 12px 0;
  font-size: 16px;
}
.btn-new {
  width: 100%;
  padding: 8px;
  background: #89b4fa;
  color: #1e1e2e;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}
.btn-new:hover { background: #74c7ec; }
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.session-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background .15s;
}
.session-item:hover { background: #313244; }
.session-item.active { background: #45475a; }
.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.btn-del {
  background: none;
  border: none;
  color: #6c7086;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}
.btn-del:hover { color: #f38ba8; }
.empty {
  text-align: center;
  color: #6c7086;
  padding: 24px 0;
  font-size: 13px;
}
</style>
