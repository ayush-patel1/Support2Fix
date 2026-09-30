# Development image for the Next.js frontend. A hardened, multi-stage
# production build (standalone output, non-root user) lands in Phase 23.
FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
