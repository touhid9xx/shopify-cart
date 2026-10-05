# frontend/Dockerfile
# syntax=docker/dockerfile:1.7

# ═══════════════════════════════════════════════════════════════════
# Stage 1 — Dependencies
# ═══════════════════════════════════════════════════════════════════
FROM node:20-alpine AS deps

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@12.8.1 --activate

# Copy package manifest + lockfile + workspace config (build approvals)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

RUN pnpm install --frozen-lockfile




# ═══════════════════════════════════════════════════════════════════
# Stage 2 — Builder
# ═══════════════════════════════════════════════════════════════════
FROM node:20-alpine AS builder

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@12.8.1 --activate

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time arg — browser will use this URL
ARG NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm build


# ═══════════════════════════════════════════════════════════════════
# Stage 3 — Runtime (Next.js standalone)
# ═══════════════════════════════════════════════════════════════════
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Standalone build artifacts
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget --spider -q http://localhost:3000 || exit 1

CMD ["node", "server.js"]
