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

# Проверяем установку
RUN ffmpeg -version && ffprobe -version

