This project expects a folder of content documents used by the agent.

Default location: `content/` (or set the CONTENT_DIR environment variable).

Supported file types: .pdf, .txt, .md (other text files are attempted as best-effort).

Important: this project requires an explicit content directory. If the configured content directory (default `content/` or set via CONTENT_DIR) does not exist, the application will raise an error on startup.

Checklist / Native binaries
- Python requirements (install into a venv): `pip install -r requirements.txt`
- Native binaries for OCR / PDF->image conversion (optional but recommended for scanned PDFs):
  - Tesseract OCR (provides `tesseract` on PATH)
  - Poppler utilities (provides `pdftoppm` used by `pdf2image`)

Windows install (quick):
1) Install Tesseract:
	- Download the Tesseract installer (e.g. from https://github.com/tesseract-ocr/tesseract/releases). Choose the latest Windows executable.
	- Run the installer and add the installation folder to your PATH (the installer often offers this option).

2) Install Poppler:
	- Download a Windows build of Poppler (e.g. from https://github.com/oschwartz10612/poppler-windows/releases).
	- Unzip and add the `bin/` folder to your PATH so `pdftoppm.exe` is accessible.

After installing these native binaries, restart your terminal/IDE. The app will print a clear warning at startup if either binary is missing and OCR will be skipped until both are available.

Run the app after creating a venv and installing dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m tinychatbot.app
```

If you prefer a reproducible, lockfile-driven workflow we recommend using `uv` (uvenv).
Once you've installed `uv` into your environment and created a lockfile, run the app with:

```powershell
# with a Python venv active
python -m pip install uv
uv lock --upgrade   ;# creates/updates uv.lock from pyproject.toml
uv run app          ;# runs the `app` script defined in pyproject.toml
```

The project includes a `[project.scripts]` entry so `uv run app` calls `tinychatbot.app:main`.
The pip steps above are a valid fallback if you don't use `uv`.

### Smoke test loader

For a quick sanity check on your content directory, run:

```powershell
python .\scripts\smoke_load.py
```

This prints the number of discovered documents plus a short preview for each file, which is handy before launching the main chat UI.
