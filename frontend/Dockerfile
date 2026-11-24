# syntax=docker/dockerfile:1

# --------------------------------------------------------------------------
# Stage 1: compile the Vite bundle
# --------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# --------------------------------------------------------------------------
# Stage 2: lightweight Nginx runtime on port 3000
# --------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:3000/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
