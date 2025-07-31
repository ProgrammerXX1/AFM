<template>
  <div class="context-menu" :style="{ top: `${y}px`, left: `${x}px` }" @click.stop>
    <div class="menu-item" @click="replace">🔄 Заменить</div>
    <div class="menu-item" @click="addToComponent">📂 Добавить в компонент</div>
    <div class="menu-item danger" @click="remove">🗑 Удалить</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  x: number
  y: number
  doc: any
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'replace', doc: any): void
  (e: 'add-to-component', doc: any): void
  (e: 'remove', doc: any): void
}>()

function replace() {
  emit('replace', props.doc)
  emit('close')
}

function addToComponent() {
  emit('add-to-component', props.doc)
  emit('close')
}

function remove() {
  emit('remove', props.doc)
  emit('close')
}

function handleOutsideClick(e: MouseEvent) {
  // Автоматически закрывает меню при клике вне него
  emit('close')
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
})

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick)
})
</script>

<style scoped>
.context-menu {
  position: absolute;
  background-color: #ffffff;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  width: 220px;
  z-index: 9999;
  padding: 4px 0;
  user-select: none;
}

.menu-item {
  padding: 10px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.menu-item:hover {
  background-color: #f0f0f0;
}

.menu-item.danger {
  color: #e53935;
}
</style>
