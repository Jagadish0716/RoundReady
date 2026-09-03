FROM node:22.14.0-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

FROM node:22.14.0-alpine AS builder

WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL
ENV NODE_ENV=production \
    NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=dependencies /app/node_modules ./node_modules
COPY package.json package-lock.json next-env.d.ts next.config.ts tsconfig.json postcss.config.mjs components.json ./
COPY app ./app
COPY components ./components
COPY lib ./lib
COPY types ./types
RUN mkdir -p public && npm run build

FROM node:22.14.0-alpine AS runtime

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]