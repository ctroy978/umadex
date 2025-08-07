# Deployment Guide for Hostinger VPS

## Initial Setup on Hostinger

### 1. SSH into your Hostinger VPS
```bash
ssh root@your-hostinger-ip
```

### 2. Install Docker and Docker Compose
```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Verify installation
docker --version
docker-compose --version
```

### 3. Clone your repository
```bash
cd /opt
git clone https://github.com/yourusername/umadex.git
cd umadex
```

### 4. Set up environment variables
```bash
# Copy the example file
cp .env.production.example .env.production

# Edit with your actual values
nano .env.production
```

Update these critical values:
- `SECRET_KEY`: Generate a new secure key
- `FRONTEND_URL`: Your domain (e.g., https://yourdomain.com)
- `NEXT_PUBLIC_API_URL`: Your domain with /api (e.g., https://yourdomain.com/api)
- SMTP settings for production email
- Keep your existing Supabase credentials

### 5. SSL Certificates
Since SSL certificates are already set up in the standard Let's Encrypt location (`/etc/letsencrypt/`), no additional setup needed. The nginx container will mount and use these certificates directly.

### 6. Update nginx config with your domain
```bash
# Edit the nginx production config
nano nginx/nginx.prod.conf

# Replace 'yourdomain.com' with your actual domain
```

### 7. Initial deployment
```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh production
```

## Ongoing Deployments

### Deploy updates
```bash
cd /opt/umadex
git pull origin main
./deploy.sh production
```

### View logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
```

### Restart services
```bash
# All services
docker-compose -f docker-compose.prod.yml restart

# Specific service
docker-compose -f docker-compose.prod.yml restart backend
```

### Stop services
```bash
docker-compose -f docker-compose.prod.yml down
```

## SSL Certificate Renewal

Set up auto-renewal with cron:
```bash
# Edit crontab
crontab -e

# Add this line for monthly renewal
0 0 1 * * certbot renew --quiet && docker-compose -f /opt/umadex/docker-compose.prod.yml restart nginx
```

## Monitoring

### Check service health
```bash
docker-compose -f docker-compose.prod.yml ps
```

### Check disk usage
```bash
df -h
docker system df
```

### Clean up old images
```bash
docker system prune -a
```

## Troubleshooting

### If containers won't start
1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Check environment variables: `cat .env.production`
3. Verify Supabase connection
4. Check disk space: `df -h`

### If frontend can't connect to backend
1. Check nginx is running: `docker-compose -f docker-compose.prod.yml ps nginx`
2. Check backend is healthy: `curl http://localhost:8000/api/health`
3. Review nginx logs: `docker-compose -f docker-compose.prod.yml logs nginx`

### Database issues
- Since you're using Supabase, check:
  - Supabase dashboard for any issues
  - Connection string in `.env.production`
  - Network connectivity to Supabase