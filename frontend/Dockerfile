FROM node:18-alpine

WORKDIR /app

# Install dependencies first as root
COPY package*.json ./
RUN npm install

# Copy app files
COPY . .

# Create necessary directories
RUN mkdir -p .next

# Create user and group, then change ownership
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001 && \
    chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

CMD ["npm", "run", "dev"]