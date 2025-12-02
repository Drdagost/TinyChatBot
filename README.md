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
id: default
display_name: Default Assistant
emoji: 🤖
description: A neutral, helpful assistant focused on accuracy and clarity.

[system_prompt]
You are a helpful and neutral assistant. Respond based on the provided context, focusing on accuracy and clarity. Avoid unnecessary enthusiasm or technical jargon unless relevant.

[style]
tone: neutral, professional
emoji_usage: minimal
formatting: standard paragraphs
```

The UI includes a dropdown to switch between available personas in real-time. The default persona is set via DEFAULT_PERSONA_ID environment variable (default: "default").

To add a custom persona:
1. Create a new .md file in the personas directory
2. Follow the structure above
3. Restart the app to load the new persona

Configuration
- `PERSONAS_DIR`: Path to persona files (default: `src/tinychatbot/personas/`).
- `DEFAULT_PERSONA_ID`: Default persona id used at startup (default: `default`).

When the app starts it will print the loaded personas to the console (id → display label). If the personas directory is empty or missing the app will continue running but without persona styles applied.

For detailed authoring notes and additional examples, see `docs/personas.md`.

## Embedding TinyChatBot in Your Website

TinyChatBot can be used as a standalone web app **or** embedded inside an existing site (e.g., a marketing or demo site) using an `<iframe>`.

This section explains how to:

1. Run TinyChatBot as a web server.
2. Embed it into another site.

---

### 1. Run TinyChatBot as a web server

TinyChatBot exposes a Gradio-based UI from `tinychatbot.app`. You can run it locally or behind a reverse proxy (Nginx, Caddy, etc.) for production.

#### Prerequisites

- Python 3.11+
- A virtual environment (recommended)
- An LLM provider key (e.g., OpenAI)
- Content loaded into a directory (e.g. `content/`)

#### Setup

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate        # on Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configure environment variables (example):

```bash
export OPENAI_API_KEY="sk-..."           # required for OpenAI provider
export CONTENT_DIR="content"             # folder with your docs
export DEFAULT_PERSONA_ID="default"      # or cheerful_support / expert_architect / etc.
export PORT=7860                         # optional; defaults to 7860
```

#### Start the app

```bash
python -m tinychatbot.app
```

By default, TinyChatBot will listen on:

* `http://0.0.0.0:${PORT}` (e.g., `http://localhost:7860`)

In production, you’ll typically:

* Run this behind a reverse proxy (Nginx, etc.), and

* Expose it via a friendly URL, e.g.:

* `https://demo.yourcompany.com/tinychatbot`

---

### 2. Embedding TinyChatBot via `<iframe>`

Once TinyChatBot is running at a stable URL, you can embed it into any web page using an `<iframe>`.

In your website’s HTML:

```html
<section id="tinychatbot-demo">
  <h2>Ask Our TinyChatBot</h2>
  <p>
    TinyChatBot is a domain expert over our documentation and content. Try asking a question!
  </p>

  <iframe
    src="https://demo.yourcompany.com/tinychatbot"
    style="
      width: 100%;
      max-width: 900px;
      height: 600px;
      border: none;
      border-radius: 12px;
      overflow: hidden;
    "
    title="TinyChatBot Demo"
    loading="lazy"
  ></iframe>
</section>
```

You can adjust `width`, `height`, and styling to match your site’s layout. The important part is the `src`, which should point at the TinyChatBot app you’re hosting.

---

### 3. Personas in the embedded demo

Personas let TinyChatBot answer in different tones/styles over the same content.

* Persona definitions live in `src/tinychatbot/personas/` as Markdown files.
* The default persona is set via the `DEFAULT_PERSONA_ID` environment variable.
* The UI provides a dropdown for switching personas at runtime.

For example, to start TinyChatBot with the **Cheerful Support** persona by default:

```bash
export DEFAULT_PERSONA_ID="cheerful_support"
python -m tinychatbot.app
```

Users can still switch personas in the embedded UI; the embedding site doesn’t need to do anything special.

---

### 4. Notes on security and privacy

* TinyChatBot uses your configured LLM provider (e.g., OpenAI) to answer questions.
* Only content under `CONTENT_DIR` is used for answers; personas change tone/style, not which content is accessed.
* If you enable `record_unknown_question()` (optional feature sending unknown questions to Pushover), ensure this behavior is acceptable for your environment and privacy policy.

For a basic, safe demo setup:

* Keep `CONTENT_DIR` to non-sensitive demo content.
* Disable or carefully configure any external logging / Pushover notifications.

## Development

### Local Development Setup

To set up TinyChatBot for local development:

1. **Create and activate a virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # On Windows
   # source .venv/bin/activate  # On macOS/Linux
   ```

2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Set required environment variables** (see Embedding section for details):
   - `OPENAI_API_KEY` (or your LLM provider key)
   - `CONTENT_DIR` (e.g., "content")

4. **Run the app**:
   ```powershell
   python -m tinychatbot.app
   ```

For a reproducible workflow, use `uv`:
```powershell
python -m pip install uv
uv lock --upgrade
uv run app
```

**Optional: Native binaries for PDF/OCR support**
- Install Tesseract OCR and Poppler for handling scanned PDFs.
- On Windows: Download from their releases and add to PATH.

### Smoke test loader

For a quick sanity check on your content directory, run:

```powershell
python .\scripts\smoke_load.py
```

This prints the number of discovered documents plus a short preview for each file, which is handy before launching the main chat UI.
