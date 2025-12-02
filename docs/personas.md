# Personas in TinyChatBot

TinyChatBot supports customizable personas that define the agent's behavior, tone, and response style. Personas are loaded from Markdown files in the personas directory.

## Authoring Personas

Each persona file is a Markdown document with the following sections:

- `[meta]`: Basic information (id, display_name, emoji, description)
- `[system_prompt]`: Instructions for the AI's behavior
- `[style]`: Tone and formatting preferences

### Notes on Persona Authoring

- Supported meta syntaxes: both `key: value` and `key = value` are accepted for the `[meta]` section (e.g. `id: default` or `id = default`).
- The `[style]` section supports simple `key: value` lines and, when PyYAML is available, richer YAML-style structures (lists, nested maps).
- Persona files must include at least `display_name` and a `[system_prompt]` section. If `id` is omitted, the filename stem will be used as the persona id.
- Adding or editing persona files requires restarting the app for changes to be picked up.

### Example Minimal Persona (YAML-friendly style block)

```markdown
[meta]
id: friendly
display_name: Friendly Assistant
emoji: 🙂

[system_prompt]
You are a friendly assistant. Keep explanations simple and warm.

[style]
tone: friendly
emoji_usage: light
formatting:
	- Use short paragraphs
	- Use bullet lists for steps
```

For more examples, see the personas in `src/tinychatbot/personas/`.