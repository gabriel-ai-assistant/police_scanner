# ---------- build stage ----------
FROM node:20-alpine AS build
WORKDIR /app

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
