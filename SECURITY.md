# Security Advisory

## Issue: Hardcoded Database Credentials (Fixed)

### Description
Previous versions of this repository contained hardcoded database credentials in configuration files. This has been resolved and hardened in commit `7564265` (replace insecure defaults, require explicit secrets via `.env`).

### Affected Files (Fixed)
- `.env.example` — Previously included an example password; now emphasises generating unique secrets
- `docker-compose.postgres.yml` — Previously embedded weak defaults; now mandates values come from `.env`

### Resolution
✅ **Fixed**: Compose now reads credentials exclusively from `.env` (no fallbacks), and the templates instruct you to create strong unique values.

### Action Required
If you cloned this repository before commit `f0eaf62`:

1. **Update your local files**:
   ```bash
   git pull origin development
   ```

2. **Review your environment files**:
   - Check `.env` (and `.env.docker` if in use) for any hardcoded passwords
   - Regenerate strong, unique credentials for `POSTGRES_PASSWORD` (and rotate if reused elsewhere)

3. **For production deployments**:
   ```bash
   # Create secure environment file
   cp .env.example .env
   openssl rand -base64 32 | tr '/+' '_-' | cut -c1-32
   # Paste the generated secret into POSTGRES_PASSWORD (and update DATABASE_URL accordingly)
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
