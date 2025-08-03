<template>
  <div class="card">
    <div class="header">
      <span class="icon">📑</span>
      <h3>Сведения по делу</h3>
    </div>

    <div class="info-grid">
      <div class="left">
        <div><span class="label">Орган:</span> {{ caseData.organization || '—' }}</div>
        <div><span class="label">Следователь:</span> {{ caseData.investigator || '—' }}</div>
        <div><span class="label">Дата регистрации:</span> {{ caseData.registration_date || '—' }}</div>
        <div><span class="label">Квалификация:</span> {{ caseData.qualification || '—' }}</div>
        <div><span class="label">Ущерб:</span> {{ caseData.damage_amount?.toLocaleString() || '—' }}</div>
        <div><span class="label">Преступный доход:</span> {{ caseData.income_amount?.toLocaleString() || '—' }}</div>
      </div>
      <div class="right">
        <div><span class="label">Дата квалификации:</span> {{ caseData.qualification_date || '—' }}</div>
        <div><span class="label">Дата обвинительного акта:</span> {{ caseData.indictment_date || '—' }}</div>
      </div>
    </div>

    <div class="button-row">
      <button class="action-btn btn-20" @click="goToIndex">🏠 Меню</button>
      <button class="action-btn btn-40" @click="goToAnalysis">📑 Квалификация</button>
      <button class="action-btn btn-40" @click="goToAnalysis">📄 Обвинительный акт</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

defineProps<{
  caseData: {
    organization: string
    investigator: string
    registration_date: string
    qualification: string
    qualification_date: string
    indictment_date: string
    damage_amount: number
    income_amount: number
  }
}>()

const router = useRouter()

const goToIndex = () => router.push({ name: 'index' })
const goToAnalysis = () => router.push({ name: 'analysis' })
</script>


<style scoped>
.btn-20 {
  flex: 0 0 15%;
}

.btn-40 {
  flex: 0 0 41%;
}

.card {
  /* background: #f9fafc; */
  padding: 14px;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
  font-family: 'Segoe UI', sans-serif;
  font-size: 13px;
}

.header {
  display: flex;
  align-items: center;
  font-weight: 600;
  margin-bottom: 10px;
  font-size: 14px;
  gap: 6px;
}

.info-grid {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  gap: 24px;
  flex-wrap: wrap;
}

.left, .right {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 180px;
  flex: 1;
}

.label {
  font-weight: 600;
  margin-right: 4px;
}

.button-row {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  /* background-color: #ffffff; */
  border: 1px solid #cbd5e1;
  color: #ffffff;
  padding: 8px 10px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: 0.2s ease background;
}

.action-btn:hover {
  background-color: #f1f5f9;
}
</style>
