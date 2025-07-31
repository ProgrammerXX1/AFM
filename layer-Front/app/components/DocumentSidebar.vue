<template>
  <aside class="sidebar">
    <!-- 🔍 Поиск -->
    <div class="search-box">
      <input type="text" placeholder="🔍 Поиск" />
    </div>

    <!-- 📄 Группы документов -->
    <div class="doc-group">
      <div class="group-title blue">Процессуальные документы</div>

      <details>
        <summary class="doc-category">Акты</summary>
        <ul>
          <li>Акт служебной проверки</li>
        </ul>
      </details>

      <ul>
        <li>Протоколы</li>
        <li>Заключения</li>
        <li>Расписки</li>
      </ul>
    </div>

    <div class="doc-group">
      <div class="group-title red">Признаки квалификации</div>
      <ul>
        <li class="law-article">Статья 217</li>
        <li class="law-article">Статья 218</li>
        <li class="law-article">Статья 262</li>
      </ul>
    </div>

    <!-- 🧾 Кнопки -->
    <div class="actions">
      <button class="btn">Отправить на согласование</button>
      <button class="btn btn-secondary">Выгрузить</button>
      <button class="btn btn-secondary" @click="goToIndex">
      Меню</button>
    </div>
  </aside>
</template>
<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
const goToIndex = () => {
  router.push({ name: 'index' })
}
</script>
<style scoped>
.sidebar {
  background-color: #f6f6f6;
  padding: 1rem;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
  color: #1e1e1e;
  font-family: sans-serif;
}

/* 🔍 Поиск */
.search-box input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #ccc;
  outline: none;
  font-size: 0.95rem;
}

/* 📂 Категории */
.doc-group {
  margin-top: 1.25rem;
}

.group-title {
  font-weight: bold;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.group-title.blue {
  color: #2563eb;
}

.group-title.red {
  color: #e11d48;
}

.doc-category {
  cursor: pointer;
  font-weight: bold;
  margin: 0.5rem 0;
}

ul {
  list-style: none;
  padding-left: 1rem;
  margin: 0.25rem 0 0.75rem 0;
}

li {
  margin-bottom: 0.3rem;
  cursor: pointer;
  font-size: 0.95rem;
}

/* 📎 Законы */
.law-article {
  padding-left: 0.5rem;
}

/* 🧾 Кнопки */
.actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: auto;
  border-top: 1px solid #ccc;
  padding-top: 1rem;
}

.btn {
  padding: 0.5rem;
  background: white;
  border: 1px solid #2563eb;
  border-radius: 6px;
  color: #2563eb;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn:hover {
  background: #2563eb;
  color: white;
}

.btn-secondary {
  border-color: #1f2937;
  color: #1f2937;
}

.btn-secondary:hover {
  background: #1f2937;
  color: white;
}
</style>
