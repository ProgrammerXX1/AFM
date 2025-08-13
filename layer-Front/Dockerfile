# ===== Build stage =====
FROM node:20-alpine AS builder

# ВАЖНО: не ставим NODE_ENV=production до npm ci,
# иначе devDependencies (включая @nuxtjs/tailwindcss) не установятся.
WORKDIR /app
RUN apk add --no-cache libc6-compat

COPY package*.json ./
# Устанавливаем и prod, и dev зависимости
RUN npm ci --no-audit --no-fund

# Копируем исходники
COPY . .

# Прокидываем публичный API_BASE для NUXT (на билд можно передать через --build-arg или env)
# Если хочешь — можно вообще не задавать здесь и отдать это на runtime через compose.
ARG API_BASE=http://back:8000
ENV NUXT_PUBLIC_API_BASE=${API_BASE}

# Собираем Nuxt (тут уже можно выставить production, но не обязательно)
RUN npm run build

# ===== Runtime stage =====
FROM node:20-alpine

WORKDIR /app
RUN apk add --no-cache libc6-compat wget

# Копируем только сборку
COPY --from=builder /app/.output /app/.output

# Прод-окружение и публичные переменные для клиента
ENV NODE_ENV=production

EXPOSE 3000
# Правильный прод-старт Nuxt 3/4
CMD ["node", ".output/server/index.mjs"]
