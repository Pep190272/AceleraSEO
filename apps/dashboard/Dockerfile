# ─────────────────────────────────────────────────────────────
# AceleraSEO dashboard — Next.js standalone build.
# Build context = apps/dashboard (see docker-compose.yml).
# ─────────────────────────────────────────────────────────────
FROM node:22-slim AS builder
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ─────────────────────────────────────────────────────────────
FROM node:22-slim AS runtime
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000

# Non-root.
RUN useradd --create-home --uid 10001 appuser

# The standalone output bundles only what's needed to run.
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

USER appuser
EXPOSE 3000

CMD ["node", "server.js"]
