@echo off
docker compose up --build -d
echo.
echo Banca Moderna iniciada.
echo Aplicativo: http://localhost:8000
echo Adminer:    http://localhost:8080
pause
