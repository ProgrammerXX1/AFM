<template>
  <div class="suspect-card">
    <h3 class="title">Подозреваемый</h3>

    <div class="info-grid">
      <div class="label-column">
        <div class="label">Фамилия</div>
        <div class="label">Имя</div>
        <div class="label">Отчество</div>
        <div class="label">ИИН</div>
      </div>
      <div class="value-column">
        <div class="value">{{ caseData?.surname || '—' }}</div>
        <div class="value">{{ caseData?.name || '—' }}</div>
        <div class="value">{{ caseData?.patronymic || '—' }}</div>
        <div class="value">{{ caseData?.iin || '—' }}</div>
      </div>
    </div>

    <div class="progress-section">
      <div class="progress-bar">
        <div class="progress" :style="{ width: filledPercentage + '%' }"></div>
      </div>
      <div class="progress-labels">
        <span class="label-text">Сведения</span>
        <span class="percentage">{{ filledPercentage }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  caseData: {
    surname?: string
    name?: string
    patronymic?: string
    iin?: string
  }
}>()

const filledPercentage = 80
</script>

<style scoped>
.suspect-card {
  /* background-color: #ffffff; */
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  font-family: 'Segoe UI', sans-serif;
  font-size: 13px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 10px;
  color: #111827;
}

.info-grid {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 6px;
  border-top: 1px solid #e5e7eb;
  padding-top: 8px;
}

.label-column,
.value-column {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-weight: 600;
  color: #374151;
}

.value {
  font-weight: 400;
  color: #1f2937;
}

.progress-section {
  margin-top: 20px;
}

.progress-bar {
  background-color: #e0f2fe;
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
}

.progress {
  background-color: #3b82f6;
  height: 100%;
  transition: width 0.3s ease;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #374151;
  margin-top: 4px;
}

.percentage {
  font-weight: 600;
  color: #1e40af;
}
</style>
