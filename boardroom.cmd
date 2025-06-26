@echo off
echo "Building and starting containerized services..."
docker compose up -d --build

rem It's good practice to wait for services to be healthy.
rem A more robust script would loop and check health endpoints.
echo "Waiting for services to initialize..."
timeout /t 10 /nobreak > nul

echo "Starting Tauri desktop application..."
pnpm tauri dev