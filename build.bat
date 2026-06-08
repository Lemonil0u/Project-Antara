@echo off
setlocal enabledelayedexpansion

title ANTARA — Build Desktop App

echo.
echo  ================================================
echo   ANTARA — Build Desktop Executable
echo  ================================================
echo.

:: ── Cek Python ──────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python tidak ditemukan. Pastikan Python sudah di-install
    echo          dan ada di PATH.
    pause
    exit /b 1
)
echo  [OK] Python ditemukan

:: ── Cek PyInstaller ─────────────────────────────────────────────────────────
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Menginstall PyInstaller...
    pip install pyinstaller
)
echo  [OK] PyInstaller siap

:: ── Cek Pywebview ───────────────────────────────────────────────────────────
python -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Menginstall pywebview...
    pip install pywebview
)
echo  [OK] pywebview siap

:: ── Bersihkan build sebelumnya ───────────────────────────────────────────────
echo.
echo  [INFO] Membersihkan build sebelumnya...
if exist "build" rmdir /s /q build
if exist "dist\ANTARA" rmdir /s /q dist\ANTARA
echo  [OK] Build lama dihapus

:: ── Jalankan PyInstaller ─────────────────────────────────────────────────────
echo.
echo  [INFO] Mulai build... (bisa 10-30 menit untuk pertama kali)
echo         Jangan tutup window ini.
echo.

python -m PyInstaller antara.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo  [ERROR] Build gagal. Lihat pesan error di atas.
    echo          Coba jalankan: pip install -r requirements.txt
    pause
    exit /b 1
)

:: ── Selesai ──────────────────────────────────────────────────────────────────
echo.
echo  ================================================
echo   BUILD SELESAI!
echo  ================================================
echo.
echo   Output ada di:
echo   dist\ANTARA\ANTARA.exe
echo.
echo   Untuk distribusi, zip seluruh folder:
echo   dist\ANTARA\
echo.
echo   JANGAN kirim hanya file .exe-nya saja —
echo   semua file di folder dist\ANTARA\ harus ikut.
echo.
pause
