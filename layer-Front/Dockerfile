FROM node:20

# Установка зависимостей
WORKDIR /app
COPY . .

# Устанавливаем только необходимые пакеты
RUN npm install

# Сборка Nuxt в прод-режиме
RUN npm run build

EXPOSE 3000

# Запускаем прод-сервер
CMD ["node", ".output/server/index.mjs"]