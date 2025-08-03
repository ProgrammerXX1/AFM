<template>
  <div class="filter-bar">
    <div class="filters">
      <!-- Вид документа -->
<div class="field">
  <label class="label">Вид документа</label>
  <div class="input-wrapper">
    
    <!-- Левая иконка -->
    <span class="icon"></span>

    <!-- Кастомный селект -->
    <select
  v-model="selectedType"
  @change="onTypeChange"
  :class="['custom-input appearance-none', { placeholder: !selectedType }]"
>
  <option value="">Вид документа</option>
  <option value="Протоколы">Протоколы</option>
  <option value="Заключений">Заключений</option>
  <option value="Постановлений">Постановлений</option>
</select>


    <!-- Крестик сброса -->
    <!-- Иконка сброса или фильтра -->
<span
  class="icon clickable"
  @click="selectedType ? resetTypeFilter() : null"
  :title="selectedType ? 'Сбросить фильтр' : 'Фильтр по типу'"
>
  {{ selectedType ? '❌' : '🎚️' }}
</span>

  </div>
</div>


      <!-- Фильтр по дате -->
<div class="field">
  <label class="label">Фильтры</label>
  <div class="input-wrapper">
    <DatePicker
      v-model="range"
      range
      :clearable="true"
      :enable-time-picker="false"
      locale="ru"
      placeholder="Дата добавления"
    />
    <!-- Иконка сброса -->
    <span
      class="icon clickable"
      @click="range ? resetDateFilter() : null"
      :title="range ? 'Сбросить фильтр' : 'Фильтр по дате'"
>
  {{ range ? '❌' : '📅' }}
</span>
  </div>
</div>

    </div>

    <!-- Поиск -->
    <div class="search">
      <label class="label">&nbsp;</label>
      <input type="text" placeholder="🔍 Поиск" @input="onInput" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import DatePicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'

  

// 🔊 События
const emit = defineEmits(['update:search', 'update:type', 'update:dateRange'])

// 📅 Диапазон по умолчанию — неделя назад до сегодня
const today = new Date()
const oneWeekAgo = new Date()
oneWeekAgo.setDate(today.getDate() - 7)

// 🧩 Состояния фильтров
const range = ref<[Date, Date] | null>([oneWeekAgo, today])
const selectedType = ref<string>('')

// 🔍 Поиск
const onInput = (event: Event) => {
  const value = (event.target as HTMLInputElement).value
  emit('update:search', value)
}

// 🗂 Тип документа выбран
const onTypeChange = (event: Event) => {
  const value = (event.target as HTMLSelectElement).value
  selectedType.value = value
  emit('update:type', value)
}

// ❌ Сброс фильтра типа
const resetTypeFilter = () => {
  selectedType.value = ''
  emit('update:type', '')
}

// ❌ Сброс фильтра даты
const resetDateFilter = () => {
  range.value = null
  emit('update:dateRange', { from: null, to: null })
}

// 🚀 Инициализация фильтра при загрузке
onMounted(() => {
  if (range.value?.length === 2) {
    emit('update:dateRange', {
      from: range.value[0],
      to: range.value[1],
    })
  }
})

// 🔁 Слежение за изменением диапазона
watch(range, (val) => {
  if (!val || val.length !== 2 || !val[0] || !val[1]) {
    emit('update:dateRange', { from: null, to: null })
    return
  }
  emit('update:dateRange', {
    from: val[0],
    to: val[1],
  })
})
</script>

<style scoped>
@import '@vuepic/vue-datepicker/dist/main.css';

/* Контейнер всей панели фильтров */
.filter-bar {
  width: 100%;
  /* background-color: #1f1f1f; */
  padding-top: 1px;
  border-radius: 10px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  box-sizing: border-box;
}

/* Группа фильтров */
.filters {
  display: flex;
  gap: 20px;
}

/* Одна фильтр-секция */
.field {
  display: flex;
  flex-direction: column;
  font-size: 13px;
}

/* Заголовок поля */
.label {
  font-weight: 500;
  margin-bottom: 4px;
  color: #363636;
  font-size: 12px;
}

/* Обёртка для input/select + иконки */
.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

/* Унифицированный стиль для инпутов и селектов */
.custom-input,
.input-wrapper :deep(.dp__input) {
  background-color: #363636;
  color: white;
  border: 1px solid #374151;
  border-radius: 8px;
  font-size: 13px;
  height: 34px;
  padding: 6px 32px 6px 36px; /* слева 📄 или 📆, справа ❌ */
  width: 220px;
  box-sizing: border-box;
  appearance: none;
}

/* Выпадающий список */
.custom-input option[disabled] {
  color: #6b7280;
  background-color: #5fc709;
}

/* Иконка слева (📄, 📆) */
.input-wrapper::before {
  content: '📄';
  position: absolute;
  left: 10px;
  font-size: 14px;
  color: #9ca3af;
  pointer-events: none;
}
.custom-input.placeholder {
  color: #9ca3af; /* светло-серый как у placeholder */
}
/* Иконка справа (❌) */
.icon {
  position: absolute;
  right: 10px;
  font-size: 14px;
  color: #9ca3af;
}

/* Кликабельная иконка */
.icon.clickable {
  cursor: pointer;
  color: #f87171;
  pointer-events: auto;
  transition: color 0.2s;
}
.icon.clickable:hover {
  color: #ef4444;
}

/* Поле поиска */
.search {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  flex-grow: 1;
  max-width: 240px;
}

.search input {
  height: 34px;
  padding: 6px 12px;
  border: 1px solid #374151;
  border-radius: 8px;
  background-color: #363636;
  font-size: 13px;
  color: white;
  width: 100%;
  box-sizing: border-box;
}
</style>
