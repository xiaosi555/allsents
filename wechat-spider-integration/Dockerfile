FROM node:16-bullseye
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN git clone --depth 1 https://github.com/lqqyt2423/wechat_spider.git /app \
    && npm install --omit=dev
# Do not reuse the upstream repository's publicly committed CA private key.
# AnyProxy will generate a fresh CA under /root/.anyproxy on first start.
RUN rm -rf /app/certificates && mkdir -p /root/.anyproxy
ENV NODE_ENV=production
ENV DEPLOY=docker
EXPOSE 8101 8104
CMD ["node", "index.js"]
