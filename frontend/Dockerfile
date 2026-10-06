# frontend/Dockerfile
# syntax=docker/dockerfile:1.7

# ═══════════════════════════════════════════════════════════════════
# Stage 1 — Dependencies
# ═══════════════════════════════════════════════════════════════════
FROM node:20-alpine AS deps

WORKDIR /app

# Enable pnpm via corepack
RUN corepack enable && corepack prepare pnpm@12.9.1 --activate

# Copy package manifest + lockfile + .npmrc (NO pnpm-workspace.yaml)
COPY package.json pnpm-lock.yaml .npmrc ./

# Install deps — allow native build scripts
RUN pnpm install --frozen-lockfile --config.strict-dep-builds=false


# ═══════════════════════════════════════════════════════════════════
# Stage 2 — Builder
# ═══════════════════════════════════════════════════════════════════
FROM node:20-alpine AS builder

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@12.9.1 --activate

# Copy node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source
COPY . .

ARG NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js app
RUN pnpm build

# Sanity check
RUN test -f /app/.next/standalone/server.js \
    || (echo "ERROR: server.js missing — check next.config.ts has output: 'standalone'" \
        && ls -la /app/.next/ && exit 1)


# ═══════════════════════════════════════════════════════════════════
# Stage 3 — Runtime
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


COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget --spider -q http://localhost:3000/ || exit 1


# DO NOT use `pnpm start` — that looks for /app/pnpm and fails
CMD ["node", "server.js"]
