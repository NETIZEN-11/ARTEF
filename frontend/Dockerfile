FROM node:20-alpine as base

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app

FROM base as builder

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --no-frozen-lockfile

COPY . .
RUN pnpm build

FROM base as runner

ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD wget --spider -q http://localhost:3000 || exit 1

CMD ["node", "server.js"]