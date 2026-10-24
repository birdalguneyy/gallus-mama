@echo off
chcp 65001 >nul
echo ====================================================
echo   GALLUS MAMA & YUMURTA - CANLI FIRESTORE SİSTEMİ
echo ====================================================
echo.
echo [1/2] Canlı E-Ticaret ve Firestore Sunucusu Başlatılıyor...
start "" /B "C:\Users\birdo\Projects\stok-satis-takip\.venv\Scripts\python.exe" "%~dp0server.py"
timeout /t 2 >nul
echo [2/2] Tarayıcı Başlatılıyor...
start "" "http://localhost:3000"
echo.
echo Sistem başarıyla çalışıyor! (http://localhost:3000)
exit
