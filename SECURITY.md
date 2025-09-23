# Security Advisory

## Issue: Hardcoded Database Credentials (Fixed in commit f0eaf62)

### Description
Previous versions of this repository contained hardcoded database credentials in configuration files. This has been resolved in commit `f0eaf62`.

### Affected Files (Fixed)
- `.env.example` - Contained example database URL with hardcoded password
- `docker-compose.postgres.yml` - Contained hardcoded PostgreSQL credentials

### Resolution
✅ **Fixed**: All hardcoded credentials have been replaced with environment variables using the `${VAR:-default}` pattern.

### Action Required
If you cloned this repository before commit `f0eaf62`:

1. **Update your local files**:
   ```bash
   git pull origin development
   ```

2. **Review your environment files**:
   - Check `.env` file for any hardcoded passwords
   - Use `.env.docker.example` as template for Docker setup
   - Generate strong, unique passwords for production

3. **For production deployments**:
   ```bash
   # Create secure environment file
   cp .env.docker.example .env.docker
   # Edit .env.docker with your secure credentials
   export POSTGRES_PASSWORD=$(openssl rand -base64 32)
   ```

### Best Practices
- ✅ Use environment variables for all secrets
- ✅ Use different passwords for each environment
- ✅ Never commit `.env` files with real credentials
- ✅ Use strong, randomly generated passwords
- ✅ Rotate credentials regularly

### Prevention
This repository now includes:
- Environment variable templates without real secrets
- Documentation emphasizing secure configuration
- Docker Compose files that require explicit environment setup