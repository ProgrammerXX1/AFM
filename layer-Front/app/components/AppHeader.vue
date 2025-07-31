```vue
<template>
  <header class="app-header relative overflow-hidden">
    <!-- Космический фон -->
    <div class="absolute inset-0 z-0 pointer-events-none">
      <svg viewBox="0 0 1280 120" class="w-full h-full">
        <!-- Определения градиентов и фильтров -->
        <defs>
          <linearGradient id="nebulaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#1f2937;stop-opacity:0.3" />
            <stop offset="50%" style="stop-color:#374151;stop-opacity:0.2" />
            <stop offset="100%" style="stop-color:#1e40af;stop-opacity:0.3" />
          </linearGradient>
          <radialGradient id="starGradient" cx="50%" cy="50%" r="50%">
            <stop offset="0%" style="stop-color:#d1d5db;stop-opacity:0.9" />
            <stop offset="100%" style="stop-color:#4b5563;stop-opacity:0.2" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <!-- Облака туманности -->
        <path
          d="M100 60 Q300 40, 500 60 T900 60 Q1000 80, 1100 60 T1280 60"
          fill="url(#nebulaGradient)"
          class="animate-nebula-drift"
          opacity="0.4"
        />
        <path
          d="M50 80 Q250 50, 450 80 T850 80 Q950 100, 1050 80 T1230 80"
          fill="url(#nebulaGradient)"
          class="animate-nebula-drift delay-1000"
          opacity="0.3"
        />

        <!-- Орбитальные линии -->
        <ellipse
          cx="640"
          cy="60"
          rx="150"
          ry="30"
          fill="none"
          stroke="url(#nebulaGradient)"
          stroke-width="1.5"
          stroke-dasharray="10 10"
          class="animate-orbit-flow"
        />
        <ellipse
          cx="640"
          cy="60"
          rx="200"
          ry="40"
          fill="none"
          stroke="url(#nebulaGradient)"
          stroke-width="1"
          stroke-dasharray="8 8"
          class="animate-orbit-flow delay-500"
        />

        <!-- Звёзды -->
        <circle
          cx="300"
          cy="40"
          r="4"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse"
        />
        <circle
          cx="900"
          cy="50"
          r="4"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse delay-500"
        />
        <circle
          cx="400"
          cy="80"
          r="3"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse delay-1000"
        />
        <circle
          cx="800"
          cy="30"
          r="3"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse delay-1500"
        />
        <circle
          cx="640"
          cy="60"
          r="6"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-soft-glow animate-spin-slow"
        />
      </svg>
    </div>

    <div class="header-container relative z-10">
      <div class="flex items-center gap-2">
        <div class="relative w-8 h-8">
          <svg viewBox="0 0 100 100" class="w-full h-full text-indigo-600 animate-pulse-tech">
            <!-- Центральный AI-ядро -->
            <circle cx="50" cy="50" r="20" fill="#6366f1" opacity="0.6" />
            <!-- Микросхемы -->
            <g stroke="#4f46e5" stroke-width="2">
              <line x1="50" y1="5" x2="50" y2="20" />
              <line x1="50" y1="80" x2="50" y2="95" />
              <line x1="5" y1="50" x2="20" y2="50" />
              <line x1="80" y1="50" x2="95" y2="50" />
            </g>
            <!-- Весы ⚖️ -->
            <text x="50%" y="55%" text-anchor="middle" font-size="16" fill="white" dy="4">
              ⚖️
            </text>
          </svg>
        </div>
        <h1 class="text-lg font-bold text-gray-900">Цифровой следопыт</h1>
      </div>

      <button class="profile-btn">Профиль</button>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  width: 100%;
  border-bottom: 1px solid #2e2e2e;
  padding: 12px 0;
}

.header-container {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.profile-btn {
  padding: 6px 14px;
  background-color: #2a2a2a;
  border: 1px solid #444;
  color: white;
  font-size: 13px;
  border-radius: 8px;
  cursor: pointer;
}

.profile-btn:hover {
  background-color: #4e4e4e;
}
</style>
```