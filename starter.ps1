# Check if tunnel credentials exist
if (-not (Test-Path ".\cloudflared\credentials.json")) {
    Write-Host "ERROR: Tunnel credentials not found!" -ForegroundColor Red
    Write-Host "Run setup first:" -ForegroundColor Yellow
    Write-Host "  cloudflared tunnel create sentinelai" -ForegroundColor Yellow
    Write-Host "  Copy-Item 'C:\Users\ACER\.cloudflared\<uuid>.json' '.\cloudflared\credentials.json'" -ForegroundColor Yellow
    Write-Host "  cloudflared tunnel route dns sentinelai sentinelai.work" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting SentinelAI..." -ForegroundColor Green
docker-compose build
docker-compose up -d

Write-Host "`nServices running:" -ForegroundColor Green
Write-Host "  https://sentinelai.work/slack/events" -ForegroundColor Cyan
Write-Host "  https://sentinelai.work/slack/oauth/callback" -ForegroundColor Cyan
