"""
launcher.py — ANTARA Desktop Launcher
======================================
Script ini menjalankan Streamlit sebagai server di background,
lalu membuka window native via pywebview.

User experience:
  1. Double-click ANTARA.exe
  2. Splash screen / loading muncul sebentar
  3. Window "ANTARA" muncul dengan UI lengkap
  4. Tutup window = app berhenti total (tidak ada proses background)

Cara build exe:
  pyinstaller antara.spec
"""

import os
import sys
import time
import socket
import threading
import subprocess
import webbrowser

import webview

# ── Konfigurasi ───────────────────────────────────────────────────────────────
APP_TITLE   = "ANTARA — Smart Route Finder"
APP_WIDTH   = 1280
APP_HEIGHT  = 800
PORT        = 8501
HOST        = "127.0.0.1"
URL         = f"http://{HOST}:{PORT}"


# ── Cari base path (beda antara .py dan .exe PyInstaller) ────────────────────
def get_base_path() -> str:
    """Return base directory — berbeda saat jalan sebagai .exe vs .py"""
    if getattr(sys, "frozen", False):
        # Jalan sebagai .exe PyInstaller
        return sys._MEIPASS
    # Jalan sebagai .py biasa
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()


# ── Set PLAYWRIGHT_BROWSERS_PATH agar scraper tahu letak Chromium ─────────────
def setup_playwright_path():
    """
    Saat jalan sebagai .exe, Chromium sudah dibundle di dalam folder _internal/.
    Set env var agar Playwright bisa menemukannya.
    """
    if getattr(sys, "frozen", False):
        # Chromium ada di dalam bundle
        browsers_path = os.path.join(BASE_PATH, "ms-playwright")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
    # Kalau jalan sebagai .py, pakai lokasi default Playwright


# ── Cari path app.py ──────────────────────────────────────────────────────────
def get_app_path() -> str:
    if getattr(sys, "frozen", False):
        # Saat jalan sebagai .exe, app.py ada di folder yang sama dengan .exe
        return os.path.join(os.path.dirname(sys.executable), "app.py")
    return os.path.join(BASE_PATH, "app.py")


# ── Tunggu Streamlit siap ─────────────────────────────────────────────────────
def wait_for_streamlit(timeout: int = 60) -> bool:
    """Poll localhost:PORT sampai Streamlit siap menerima koneksi."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.3)
    return False


# ── Jalankan Streamlit di background thread ───────────────────────────────────
_streamlit_proc = None

def start_streamlit():
    global _streamlit_proc
    app_path = get_app_path()

    # Cari Python / streamlit executable
    python_exe = sys.executable if not getattr(sys, "frozen", False) else "python"

    cmd = [
        python_exe, "-m", "streamlit", "run", app_path,
        "--server.port", str(PORT),
        "--server.address", HOST,
        "--server.headless", "true",       # Jangan buka browser otomatis
        "--server.runOnSave", "false",
        "--client.showErrorDetails", "false",
        "--client.toolbarMode", "minimal",  # Sembunyikan toolbar Streamlit
        "--browser.gatherUsageStats", "false",
        "--theme.base", "light",
    ]

    _streamlit_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(get_app_path()),
    )


def stop_streamlit():
    global _streamlit_proc
    if _streamlit_proc:
        _streamlit_proc.terminate()
        try:
            _streamlit_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _streamlit_proc.kill()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    setup_playwright_path()

    # Mulai Streamlit di background
    streamlit_thread = threading.Thread(target=start_streamlit, daemon=True)
    streamlit_thread.start()

    # Buat window dengan loading screen sementara Streamlit siap
    window = webview.create_window(
        title   = APP_TITLE,
        url     = "data:text/html,<html><body style='background:#f0fafa;display:flex;"
                  "justify-content:center;align-items:center;height:100vh;margin:0;"
                  "font-family:Segoe UI,sans-serif;'>"
                  "<div style='text-align:center'>"
                  "<p style='font-size:32px;font-weight:800;color:#26a69a;margin:0'>antara</p>"
                  "<p style='color:#64748b;margin-top:8px'>Memuat aplikasi...</p>"
                  "</div></body></html>",
        width   = APP_WIDTH,
        height  = APP_HEIGHT,
        resizable     = True,
        min_size      = (900, 600),
        background_color = "#f0fafa",
    )

    def on_loaded():
        """Callback saat window sudah dibuat — tunggu Streamlit lalu navigasi."""
        ready = wait_for_streamlit(timeout=90)
        if ready:
            window.load_url(URL)
        else:
            # Streamlit gagal start — tampilkan pesan error
            window.load_html("""
            <html><body style='font-family:Segoe UI;display:flex;justify-content:center;
            align-items:center;height:100vh;'>
            <div style='text-align:center'>
                <p style='font-size:24px;color:#ef4444;'>Gagal memulai aplikasi</p>
                <p style='color:#64748b'>Pastikan semua dependencies sudah terinstall.</p>
                <p style='color:#64748b'>Coba jalankan: pip install -r requirements.txt</p>
            </div></body></html>
            """)

    # Jalankan callback di thread terpisah agar tidak block UI
    threading.Thread(target=on_loaded, daemon=True).start()

    # Start webview — blocking sampai window ditutup
    webview.start(debug=False)

    # Setelah window ditutup, hentikan Streamlit
    stop_streamlit()


if __name__ == "__main__":
    main()
