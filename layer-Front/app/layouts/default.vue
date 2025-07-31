```vue
<template>
  <AppHeader />
  <div class="relative min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-blue-950 overflow-hidden">
    <!-- Космический фон -->
    <div class="absolute inset-0 z-0 pointer-events-none">
      <svg viewBox="0 0 1200 800" class="w-full h-full">
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
            <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <!-- Облака туманности -->
        <path
          d="M100 400 Q300 300, 500 400 T900 400 Q1000 500, 1100 400 T1200 400"
          fill="url(#nebulaGradient)"
          class="animate-nebula-drift"
          opacity="0.4"
        />
        <path
          d="M50 450 Q250 350, 450 450 T850 450 Q950 550, 1050 450 T1150 450"
          fill="url(#nebulaGradient)"
          class="animate-nebula-drift delay-1000"
          opacity="0.3"
        />
        <path
          d="M150 350 Q350 250, 550 350 T950 350 Q1050 450, 1150 350 T1200 350"
          fill="url(#nebulaGradient)"
          class="animate-nebula-drift delay-2000"
          opacity="0.2"
        />

        <!-- Орбитальные линии -->
        <ellipse
          cx="600"
          cy="400"
          rx="200"
          ry="100"
          fill="none"
          stroke="url(#nebulaGradient)"
          stroke-width="2"
          stroke-dasharray="15 15"
          class="animate-orbit-flow"
        />
        <ellipse
          cx="600"
          cy="400"
          rx="250"
          ry="120"
          fill="none"
          stroke="url(#nebulaGradient)"
          stroke-width="1.5"
          stroke-dasharray="10 10"
          class="animate-orbit-flow delay-500"
        />
        <ellipse
          cx="600"
          cy="400"
          rx="150"
          ry="80"
          fill="none"
          stroke="url(#nebulaGradient)"
          stroke-width="1"
          stroke-dasharray="8 8"
          class="animate-orbit-flow delay-1000"
        />

        <!-- Звёзды -->
        <circle
          cx="300"
          cy="200"
          r="5"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse"
        />
        <circle
          cx="900"
          cy="300"
          r="5"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse delay-500"
        />
        <circle
          cx="400"
          cy="500"
          r="4"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse delay-1000"
        />
        <circle
          cx="800"
          cy="150"
          r="4"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse delay-1500"
        />
        <circle
          cx="600"
          cy="400"
          r="8"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-soft-glow animate-spin-slow"
        />
        <circle
          cx="500"
          cy="300"
          r="3"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse delay-2000"
        />
        <circle
          cx="700"
          cy="500"
          r="3"
          fill="url(#starGradient)"
          filter="url(#glow)"
          class="animate-star-pulse delay-2500"
        />
      </svg>
    </div>

    <!-- Контент поверх -->
    <div class="relative z-10">
      <NuxtPage />
    </div>
  </div>
</template>

<script setup>
// Нет необходимости в дополнительной логике, так как анимации управляются Tailwind
</script>
```