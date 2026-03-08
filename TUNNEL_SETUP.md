# Cloudflare Tunnel Setup

Run these commands on your local machine (not in Docker):

```powershell
# 1. Login to Cloudflare
cloudflared tunnel login

# 2. Create named tunnel
cloudflared tunnel create sentinelai

# 3. Copy the credentials file to the project
# The command above will show you the path to the credentials file
# Copy it to: ./cloudflared/credentials.json

# 4. Create DNS records
cloudflared tunnel route dns sentinelai sentinelai.work
cloudflared tunnel route dns sentinelai www.sentinelai.work

# 5. Start the services
docker-compose up -d
```

Your endpoints will be:
- https://sentinelai.work/slack/events
- https://sentinelai.work/slack/oauth/callback
