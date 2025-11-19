# Л.И.С.А. - N8N с FFmpeg для медиа-обработки
# Базовый образ n8n + FFmpeg для обработки видео/аудио в workflows

FROM n8nio/n8n:latest

USER root
RUN apk update && apk add --no-cache ffmpeg && rm -rf /var/cache/apk/*

USER node
RUN ffmpeg -version && ffprobe -version
