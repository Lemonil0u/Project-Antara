# antara.spec — PyInstaller build spec untuk ANTARA
# 
# Cara pakai:
#   pyinstaller antara.spec
#
# Output ada di folder dist/ANTARA/
# File yang bisa didistribusikan: folder dist/ANTARA/ (zip seluruh folder ini)

import os
import sys
from pathlib import Path

# ── Path project ──────────────────────────────────────────────────────────────
PROJECT_DIR   = Path(r"D:\el\Polban\Project 1\ANTARA_PROJECT")
PLAYWRIGHT_DIR = Path(r"C:\Users\HP\AppData\Local\ms-playwright")

# ── Validasi path ada ─────────────────────────────────────────────────────────
assert PROJECT_DIR.exists(), f"Project tidak ditemukan: {PROJECT_DIR}"
assert PLAYWRIGHT_DIR.exists(), f"Playwright tidak ditemukan: {PLAYWRIGHT_DIR}"

# ── Kumpulkan semua file data project ─────────────────────────────────────────
def collect_project_files(base: Path):
    """
    Kumpulkan semua file non-.py dari project untuk disertakan di bundle.
    Format: list of (src_path, dest_folder_in_bundle)
    """
    result = []
    include_exts = {
        ".css", ".md", ".txt", ".json", ".yaml", ".yml",
        ".png", ".jpg", ".jpeg", ".svg", ".ico", ".gif",
        ".html", ".db", ".sql",
    }
    include_dirs = {"assets", "data", "pages", "engine", "scraper", "database"}

    for item in base.rglob("*"):
        if item.is_file():
            # Skip pycache dan .git
            if any(part.startswith(("__pycache__", ".git", ".venv", "venv", "dist", "build"))
                   for part in item.parts):
                continue
            # Include semua file dengan ekstensi yang diizinkan
            if item.suffix.lower() in include_exts:
                rel = item.parent.relative_to(base)
                result.append((str(item), str(rel) if str(rel) != "." else "."))

    return result


project_datas = collect_project_files(PROJECT_DIR)

# Tambahkan Chromium (wajib untuk scraper)
# Hanya ambil folder chromium-1217 (yang terinstall)
chromium_dir = PLAYWRIGHT_DIR / "chromium-1217"
assert chromium_dir.exists(), f"Chromium tidak ditemukan: {chromium_dir}"

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [str(PROJECT_DIR / "launcher.py")],  # Entry point
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[
        # File project
        *project_datas,

        # Semua .py file project (pages, engine, scraper, database)
        (str(PROJECT_DIR / "app.py"),               "."),
        (str(PROJECT_DIR / "models.py"),             "."),
        (str(PROJECT_DIR / "style.css"),             "."),
        (str(PROJECT_DIR / "requirements.txt"),      "."),

        # Pages
        (str(PROJECT_DIR / "pages"),                 "pages"),

        # Engine
        (str(PROJECT_DIR / "engine"),                "engine"),

        # Scraper
        (str(PROJECT_DIR / "scraper"),               "scraper"),

        # Database
        (str(PROJECT_DIR / "database"),              "database"),

        # Assets
        (str(PROJECT_DIR / "assets"),                "assets"),

        # Chromium untuk Playwright scraper
        (str(chromium_dir), "ms-playwright/chromium-1217"),
    ],
    hiddenimports=[
        # Streamlit
        "streamlit",
        "streamlit.web.cli",
        "streamlit.runtime.scriptrunner",
        "streamlit.runtime.state",

        # Plotly
        "plotly",
        "plotly.graph_objects",
        "plotly.express",

        # Playwright
        "playwright",
        "playwright.async_api",
        "playwright.sync_api",

        # Database
        "sqlite3",

        # Project modules
        "models",
        "database",
        "database.database",
        "engine",
        "engine.optimizer",
        "engine.data_source",
        "engine.visualizer",
        "engine.local_data",
        "scraper",
        "scraper.base_scraper",
        "scraper.train_scraper",
        "scraper.plane_scraper",
        "scraper.bus_scraper",

        # Pages
        "pages.dashboard",
        "pages.loading",
        "pages.result",
        "pages.visualization",
        "pages.favorite_routes",
        "pages.profile",
        "pages.settings",
        "pages.login",
        "pages.signup",
        "pages.components.sidebar",
        "pages.components.theme",

        # Webview
        "webview",
        "webview.platforms.winforms",

        # Utils
        "asyncio",
        "threading",
        "concurrent.futures",
        "pandas",
        "numpy",
        "PIL",
        "requests",
        "bs4",
        "python_dateutil",
        "dateutil",
        "dateutil.parser",
        "pkg_resources",
        "packaging",
        "click",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Hal-hal yang tidak dibutuhkan (kurangi ukuran)
        "matplotlib",
        "scipy",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "setuptools",
        "unittest",
        "tkinter",
        "wx",
        "PyQt5",
        "PyQt6",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# ── Collect semua file ────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ANTARA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,          # Kompres binary (kurangi ukuran ~20%)
    console=False,     # Tidak tampilkan terminal saat jalan
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/logo_antara.ico",  # Uncomment jika ada file .ico
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ANTARA",  # Nama folder output di dist/
)
