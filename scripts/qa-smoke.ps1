$ErrorActionPreference = "Stop"

Write-Host "Starting core services..."
docker compose up -d --build postgres redis mongo zookeeper kafka auth-service user-service api-gateway

Start-Sleep -Seconds 10

Write-Host "Health checks..."
Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing | Out-Null
Invoke-WebRequest -Uri "http://localhost:8002/health" -UseBasicParsing | Out-Null
Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing | Out-Null

Write-Host "Smoke test completed."
