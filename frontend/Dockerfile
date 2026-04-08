# Stage 1: build frontend
FROM node:20-alpine AS builder

WORKDIR /app

# Build-time env vars (passed via docker-compose build.args)
ARG VITE_API_BASE_URL
ARG VITE_PAYMENTS_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_PAYMENTS_URL=$VITE_PAYMENTS_URL

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: nginx
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
