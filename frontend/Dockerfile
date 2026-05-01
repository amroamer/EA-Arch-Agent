FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --no-fund --no-audit

COPY . .

# ── Dev stage (default for docker-compose.yml) ──────────────────────────
FROM base AS dev
EXPOSE 5173
CMD ["npm", "run", "dev"]

# ── Production stage (docker-compose.prod.yml) ──────────────────────────
FROM base AS production
RUN npm run build
# Static assets are served by nginx in prod (see docker-compose.prod.yml).
# As a fallback the container can also `npm run preview`.
EXPOSE 5173
CMD ["npm", "run", "preview"]
