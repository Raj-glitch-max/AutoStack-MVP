# AutoStack MVP - Setup Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AutoStack MVP - Local Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (!(Test-Path "autostack-backend\.env")) {
    Write-Host "[1/4] Creating .env file from example..." -ForegroundColor Yellow
    Copy-Item "autostack-backend\.env.example" "autostack-backend\.env"
    Write-Host "✓ Created autostack-backend\.env" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Edit autostack-backend\.env and fill in:" -ForegroundColor Yellow
    Write-Host "   - SECRET_KEY" -ForegroundColor White
    Write-Host "   - GITHUB_CLIENT_ID & GITHUB_CLIENT_SECRET" -ForegroundColor White
    Write-Host "   - GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET" -ForegroundColor White
    Write-Host ""
}
else {
    Write-Host "[1/4] .env file already exists" -ForegroundColor Green
}

# Stop existing containers
Write-Host "[2/4] Stopping existing containers..." -ForegroundColor Yellow
docker-compose down 2>$null
Write-Host "✓ Stopped" -ForegroundColor Green

# Build images
Write-Host "[3/4] Building Docker images..." -ForegroundColor Yellow
docker-compose build --no-cache backend
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Built successfully" -ForegroundColor Green

# Start services
Write-Host "[4/4] Starting services..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start services" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete! 🎉" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "To view logs: docker-compose logs -f" -ForegroundColor Yellow
Write-Host "To stop:      docker-compose down" -ForegroundColor Yellow
Write-Host ""
