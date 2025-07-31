/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './components/**/*.{vue,js,ts}',
    './layouts/**/*.{vue,js,ts}',
    './pages/**/*.{vue,js,ts}',
    './app.vue',
  ],
  theme: {
    extend: {
      animation: {
        'star-pulse': 'star-pulse 3s ease-in-out infinite',
        'nebula-drift': 'nebula-drift 10s linear infinite',
        'orbit-flow': 'orbit-flow 8s linear infinite',
        'soft-glow': 'soft-glow 4s ease-in-out infinite',
        'spin-slow': 'spin-slow 15s linear infinite',
        'pulse-tech': 'pulse-tech 2s ease-in-out infinite',
      },
      keyframes: {
        'star-pulse': {
          '0%, 100%': { opacity: '0.3', transform: 'scale(1)' },
          '50%': { opacity: '0.8', transform: 'scale(1.2)' },
        },
        'nebula-drift': {
          '0%': { transform: 'translate(0, 0)', opacity: '0.2' },
          '50%': { transform: 'translate(30px, -20px)', opacity: '0.4' },
          '100%': { transform: 'translate(0, 0)', opacity: '0.2' },
        },
        'orbit-flow': {
          '0%': { strokeDashoffset: '0' },
          '100%': { strokeDashoffset: '50' },
        },
        'soft-glow': {
          '0%, 100%': { opacity: '0.5', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.3)' },
        },
        'spin-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'pulse-tech': {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.9' },
          '50%': { transform: 'scale(1.15)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}