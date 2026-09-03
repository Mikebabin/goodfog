# Build context is the repo root (see docker-compose.yml).
FROM node:22-alpine AS build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend .
# Coolify passes SOURCE_COMMIT as a build arg (see docker-compose.yml); the footer shows the short sha.
ARG SOURCE_COMMIT=dev
ENV VITE_COMMIT=${SOURCE_COMMIT}
RUN npm run build

FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/frontend/dist /usr/share/nginx/html
EXPOSE 80
