# Л.И.С.А. - N8N с FFmpeg для медиа-обработки
# Базовый образ n8n + FFmpeg для обработки видео/аудио в workflows
# Используем статические бинарники FFmpeg (n8n теперь использует минимальный базовый образ без пакетного менеджера)

# Stage 1: Скачиваем статические бинарники FFmpeg
FROM alpine:latest AS ffmpeg-downloader
RUN apk add --no-cache wget xz && \
    wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -O /tmp/ffmpeg.tar.xz && \
    mkdir -p /ffmpeg && \
    tar -xf /tmp/ffmpeg.tar.xz -C /tmp && \
    mv /tmp/ffmpeg-*-amd64-static/ffmpeg /ffmpeg/ffmpeg && \
    mv /tmp/ffmpeg-*-amd64-static/ffprobe /ffmpeg/ffprobe && \
    chmod +x /ffmpeg/ffmpeg /ffmpeg/ffprobe

# Stage 2: n8n с FFmpeg
FROM n8nio/n8n:latest

COPY --from=ffmpeg-downloader /ffmpeg/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg-downloader /ffmpeg/ffprobe /usr/local/bin/ffprobe

RUN ffmpeg -version && ffprobe -version
