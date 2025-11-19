# Л.И.С.А. - N8N с FFmpeg для медиа-обработки
# Базовый образ n8n + FFmpeg для обработки видео/аудио в workflows

FROM n8nio/n8n:latest

# Переключаемся на root для установки пакетов
USER root

# Устанавливаем FFmpeg (включает ffmpeg, ffprobe, ffplay)
RUN apk update && \
    apk add --no-cache ffmpeg && \
    rm -rf /var/cache/apk/*

# Возвращаемся к пользователю node (стандартный для n8n)
USER node

# Создаем директорию для пользовательских нод, если её нет
RUN mkdir -p /home/node/.n8n/nodes

# Создаем package.json с overrides для решения проблем совместимости зависимостей
# Это автоматически применится ко всем устанавливаемым пользовательским нодам
RUN echo '{ \
  "name": "n8n-custom-nodes", \
  "version": "1.0.0", \
  "description": "Package configuration for n8n custom nodes with dependency overrides", \
  "dependencies": { \
    "zod": "3.24.1" \
  }, \
  "overrides": { \
    "zod": "^3.24.1" \
  } \
}' > /home/node/.n8n/nodes/package.json

# Устанавливаем совместимую версию zod для гарантии совместимости
# Это гарантирует, что все пакеты будут использовать одну и ту же версию
RUN npm install --prefix /home/node/.n8n/nodes

# Проверяем установку
RUN ffmpeg -version && ffprobe -version

