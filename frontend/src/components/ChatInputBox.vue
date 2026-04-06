<template>
  <div class="input-box">
    <label v-if="serviceType === 'remotesam'" class="img-picker">
      <input type="file" accept="image/*" @change="onFileChange" />
      <span>{{ imageFile ? imageFile.name : '选择图片' }}</span>
    </label>
    <textarea
      ref="inputEl"
      v-model="text"
      :placeholder="serviceType === 'remotesam' ? '输入遥感问题描述（例如: the airplane on the right）' : '输入你的编程问题…'"
      :disabled="loading"
      @keydown.enter.exact.prevent="submit"
      rows="1"
    />
    <button class="btn-send" :disabled="loading || !text.trim()" @click="submit">
      {{ loading ? '思考中…' : '发送' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ loading: boolean; serviceType: 'qwen' | 'remotesam' }>()
const emit = defineEmits<{
  (e: 'send', payload: { text: string; imageFile: File | null }): void
}>()

const text = ref('')
const inputEl = ref<HTMLTextAreaElement>()
const imageFile = ref<File | null>(null)

function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  imageFile.value = input.files?.[0] ?? null
}

function submit() {
  const val = text.value.trim()
  if (!val || props.loading) return
  emit('send', { text: val, imageFile: imageFile.value })
  text.value = ''
  if (props.serviceType === 'remotesam') {
    imageFile.value = null
  }
}
</script>

<style scoped>
.input-box {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 12px 20px;
  background: #1e1e2e;
  border-top: 1px solid #313244;
}
.img-picker {
  position: relative;
  overflow: hidden;
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid #45475a;
  color: #cdd6f4;
  background: #11111b;
  cursor: pointer;
  white-space: nowrap;
  font-size: 13px;
}
.img-picker input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
textarea {
  flex: 1;
  resize: none;
  border: 1px solid #45475a;
  border-radius: 8px;
  background: #11111b;
  color: #cdd6f4;
  padding: 10px 14px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  min-height: 42px;
  max-height: 160px;
}
textarea:focus { border-color: #89b4fa; }
.btn-send {
  padding: 0 20px;
  background: #89b4fa;
  color: #1e1e2e;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.btn-send:disabled { opacity: .5; cursor: not-allowed; }
.btn-send:not(:disabled):hover { background: #74c7ec; }
</style>
