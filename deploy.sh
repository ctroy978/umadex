#!/bin/bash

# Deployment script for Hostinger VPS
# Usage: ./deploy.sh [staging|production]

set -e

ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

echo "🚀 Starting deployment for $ENVIRONMENT environment..."

# Check if env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: $ENV_FILE not found!"
    echo "Please create it from .env.production.example"
    exit 1
fi

# Pull latest changes
echo "📥 Pulling latest changes from git..."
git pull origin main

# Build and deploy
echo "🔨 Building Docker images..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE build

echo "🔄 Stopping old containers..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE down

echo "🚀 Starting new containers..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo "✅ Checking service status..."
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE ps

# Show logs for debugging if needed
echo "📋 Recent logs:"
docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE logs --tail=50

echo "✨ Deployment complete!"
echo "🌐 Your application should be available at your configured domain"