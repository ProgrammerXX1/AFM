```vue
<template>
  <div class="flex justify-center items-center my-0">
    <svg viewBox="0 0 400 200" class="w-[80rem] h-[15rem]">
      <!-- Определения градиентов и фильтров -->
      <defs>
        <linearGradient id="nebulaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#1e3a8a;stop-opacity:0.3" />
          <stop offset="50%" style="stop-color:#6b21a8;stop-opacity:0.2" />
          <stop offset="100%" style="stop-color:#06b6d4;stop-opacity:0.3" />
        </linearGradient>
        <radialGradient id="starGradient" cx="50%" cy="50%" r="50%">
          <stop offset="0%" style="stop-color:#e0f2fe;stop-opacity:0.9" />
          <stop offset="100%" style="stop-color:#38bdf8;stop-opacity:0.2" />
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
        d="M50 100 Q80 70, 120 100 T200 100 Q240 130, 280 100 T350 100"
        fill="url(#nebulaGradient)"
        class="animate-nebula-drift"
      />
      <path
        d="M30 120 Q70 90, 110 120 T190 120 Q230 150, 270 120 T340 120"
        fill="url(#nebulaGradient)"
        class="animate-nebula-drift delay-1000"
        opacity="0.5"
      />

      <!-- Орбитальные линии -->
      <ellipse
        cx="200"
        cy="100"
        rx="60"
        ry="30"
        fill="none"
        stroke="url(#nebulaGradient)"
        stroke-width="1"
        stroke-dasharray="10 10"
        class="animate-orbit-flow"
      />
      <ellipse
        cx="200"
        cy="100"
        rx="80"
        ry="40"
        fill="none"
        stroke="url(#nebulaGradient)"
        stroke-width="1"
        stroke-dasharray="8 8"
        class="animate-orbit-flow delay-500"
      />

      <!-- Звёзды -->
      <circle
        cx="100"
        cy="80"
        r="3"
        fill="url(#starGradient)"
        filter="url(#glow)"
        class="animate-star-pulse"
      />
      <circle
        cx="300"
        cy="120"
        r="3"
        fill="url(#starGradient)"
        filter="url(#glow)"
        class="animate-star-pulse delay-500"
      />
      <circle
        cx="150"
        cy="140"
        r="2"
        fill="url(#starGradient)"
        filter="url(#glow)"
        class="animate-star-pulse delay-1000"
      />
      <circle
        cx="250"
        cy="60"
        r="2"
        fill="url(#starGradient)"
        filter="url(#glow)"
        class="animate-star-pulse delay-1500"
      />
      <circle
        cx="200"
        cy="100"
        r="5"
        fill="url(#starGradient)"
        filter="url(#glow)"
        class="animate-soft-glow animate-spin-slow"
      />

      <!-- DOCUMENT ICON (слева) -->
      <g transform="translate(40, 70)">
        <rect
          width="30"
          height="40"
          fill="#f3f4f6"
          stroke="#94a3b8"
          stroke-width="1.5"
          rx="2"
          class="animate-pulse-tech"
        />
        <line x1="5" y1="10" x2="25" y2="10" stroke="#64748b" stroke-width="1" />
        <line x1="5" y1="17" x2="25" y2="17" stroke="#64748b" stroke-width="1" />
        <line x1="5" y1="24" x2="20" y2="24" stroke="#64748b" stroke-width="1" />
      </g>

      <!-- LAW ICON (справа) -->
      <g transform="translate(325, 75)">
        <circle
          cx="15"
          cy="15"
          r="15"
          fill="#ede9fe"
          stroke="#7c3aed"
          stroke-width="2"
          class="animate-pulse-tech"
        />
        <text
          x="15"
          y="19"
          text-anchor="middle"
          font-size="16"
          fill="#7c3aed"
          font-weight="bold"
        >
          ⚖️
        </text>
      </g>
    </svg>
  </div>
</template>

<script setup>
// Нет необходимости в дополнительной логике, так как анимации управляются Tailwind
</script>
```