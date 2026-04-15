# ─────────────────────────────────────────────────────────────────────────────
# MarcoAI – Multi-stage Dockerfile for Nginx + React
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Build the React application using Node
FROM node:20-alpine AS build-stage

WORKDIR /app

# Copy dependency manifests first for better caching
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies (only production if needed, but vite requires devDeps)
RUN npm install

# Copy the rest of the frontend source code
COPY frontend/ ./

# Run the build script (vite build produces files in /app/dist)
RUN npm run build

# Stage 2: Serve the static files using Nginx
FROM nginx:1.27-alpine

# Copy the built files from the previous stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# The standard Nginx configuration for MarcoAI
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
