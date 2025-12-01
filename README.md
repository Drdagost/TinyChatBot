This project expects a folder of content documents used by the agent.

Default location: `content/` (or set the CONTENT_DIR environment variable).

Supported file types: .pdf, .txt, .md (other text files are attempted as best-effort).

Important: this project requires an explicit content directory. If the configured content directory (default `content/` or set via CONTENT_DIR) does not exist, the application will raise an error on startup.

## Personas

TinyChatBot supports customizable personas that define the agent's behavior, tone, and response style. Personas are loaded from Markdown files in the personas directory.

Default location: `src/tinychatbot/personas/` (or set the PERSONAS_DIR environment variable).

Each persona file is a Markdown document with the following sections:

- `[meta]`: Basic information (id, display_name, emoji, description)
- `[system_prompt]`: Instructions for the AI's behavior
- `[style]`: Tone and formatting preferences

Example persona file:

```markdown
[meta]
id=default
display_name=Default Assistant
emoji=🤖
description=A neutral, helpful assistant focused on accuracy and clarity.

[system_prompt]
You are a helpful and neutral assistant. Respond based on the provided context, focusing on accuracy and clarity. Avoid unnecessary enthusiasm or technical jargon unless relevant.

[style]
tone=neutral, professional
emoji_usage=minimal
formatting=standard paragraphs
```

The UI includes a dropdown to switch between available personas in real-time. The default persona is set via DEFAULT_PERSONA_ID environment variable (default: "default").

To add a custom persona:
1. Create a new .md file in the personas directory
2. Follow the structure above
3. Restart the app to load the new persona

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
