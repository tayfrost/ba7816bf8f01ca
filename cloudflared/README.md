# Cloudflared Tunnel Configuration

## Current Setup
This tunnel is already configured and connected to the **sentinelai.work** domain.

## ⚠️ **CRITICAL: PRODUCTION SECURITY WARNING** ⚠️
**🔴 BEFORE PRODUCTION: CHANGE THE TUNNEL CREDENTIALS 🔴**

The current `credentials.json` contains a tunnel ID that's been committed to the repo. Anyone with these credentials can intercept traffic. Before going live with real client data:
1. Generate new tunnel credentials
2. Add `credentials.json` to `.gitignore`
3. Use environment variables or secrets management

---

## Current Routing Configuration

The `config.yml` currently routes traffic to the **webhooks container**.

### For Other Developers

If you're adding new endpoints:

**Option 1: Use Existing Webhook Container**
- Add your endpoints and logic inside the `webhooks/` folder
- Everything will automatically route through the existing container

**Option 2: Use Reverse Proxy**
- Set up a reverse proxy (nginx, traefik, etc.)
- Update `config.yml` to point to the reverse proxy
- Configure the proxy to route to your specific services/containers

---

## Files
- `config.yml` - Tunnel routing configuration
- `credentials.json` - Tunnel authentication (⚠️ rotate before production)
