FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY . ./
RUN npm run build || echo "build skipped (stub)"
EXPOSE 3000
CMD ["npm","start"]
