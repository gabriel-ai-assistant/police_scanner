# ---------- build stage ----------
FROM node:20-alpine AS build
WORKDIR /app

# Build arguments for Vite environment variables
ARG VITE_API_URL=/api
ARG VITE_MOCK=0
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID

# Set as environment variables for the build
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_MOCK=$VITE_MOCK
ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
ENV VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
ENV VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID

# if you have package-lock.json, copy it too and use `npm ci`
COPY package.json ./
# COPY package-lock.json ./

# install with dev deps (needed to run vite build)
# If you have a lockfile, prefer: RUN npm ci
RUN npm install

# bring in the rest and build
COPY . .
RUN npm run build

# ---------- runtime stage ----------
FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
