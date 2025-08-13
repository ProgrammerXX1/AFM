# ===== Build stage =====
FROM node:20-alpine AS builder

ARG NODE_ENV=production
ARG API_BASE=http://back:8000
ENV NODE_ENV=${NODE_ENV}
WORKDIR /app

# nuxt требует libc6-compat иногда
RUN apk add --no-cache libc6-compat

COPY package*.json ./
RUN npm ci

COPY . .

# прокинем API_BASE в публичные рантайм-переменные Nuxt
# для Nuxt 3/4 используйте NUXT_PUBLIC_*
ENV NUXT_PUBLIC_API_BASE=${API_BASE}

RUN npm run build

# ===== Runtime stage =====
FROM node:20-alpine

WORKDIR /app
RUN apk add --no-cache libc6-compat

# копируем только сборку
COPY --from=builder /app/.output /app/.output

ENV NODE_ENV=production \
    NUXT_PUBLIC_API_BASE=${API_BASE}

EXPOSE 3000
# Правильный прод-старт Nuxt
CMD ["node", ".output/server/index.mjs"]
