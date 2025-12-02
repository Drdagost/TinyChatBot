import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Persona:
    id: str
    display_name: str
    emoji: str
    description: str
    system_prompt: str
    style: Dict[str, Any]


@dataclass
class PersonaSummary:
    id: str
    display_name: str
    description: str


def load_personas(personas_dir: str | Path) -> Dict[str, Persona]:
    personas: Dict[str, Persona] = {}
    personas_path = Path(personas_dir)
    if not personas_path.is_dir():
        return personas

    for md_file in personas_path.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            # pass filename so parser can fall back to filename-derived id
            persona = parse_persona(content, source_filename=md_file.stem)
            if persona:
                if persona.id in personas:
                    logging.warning(
                        f"Duplicate persona id '{persona.id}' found in {md_file}; skipping."
                    )
                else:
                    personas[persona.id] = persona
            else:
                logging.warning(f"Failed to parse persona from {md_file}; skipping.")
        except Exception as e:
            logging.exception(f"Error loading persona {md_file}: {e}")
    return personas


def parse_persona(content: str, source_filename: str | None = None) -> Persona | None:
    """Parse a persona markdown file into a Persona object.

    The parser accepts `key: value` and `key = value` styles in the meta section.
    The `style` section is parsed with `yaml.safe_load` when available, otherwise
    it falls back to a simple `key: value` parser.
    """
    sections: Dict[str, List[str]] = {}
    current_section: str | None = None
    lines: List[str] = content.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].lower()
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(line)

    meta_text = "\n".join(sections.get("meta", [])).strip()
    system_prompt = "\n".join(sections.get("system_prompt", [])).strip()
    style_text = "\n".join(sections.get("style", [])).strip()

    # Parse meta (allow ':' or '=')
    meta_lines: List[str] = [line for line in meta_text.split("\n") if line.strip()]
    meta_dict: Dict[str, str] = {}
    for line in meta_lines:
        m = re.match(r"^\s*([^:=]+)\s*[:=]\s*(.*)$", line)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            meta_dict[key] = value

    pid = meta_dict.get("id")
    display_name = meta_dict.get("display_name") or meta_dict.get("display-name")
    emoji = meta_dict.get("emoji", "")
    description = meta_dict.get("description", "")

    # Parse style using YAML if available for richer structure
    style: Dict[str, Any] = {}
    if style_text:
        try:
            import yaml

            parsed = yaml.safe_load(style_text)
            if isinstance(parsed, dict):
                style = parsed
        except Exception:
            # Fallback: simple key:value lines
            logging.debug(
                f"YAML parsing failed for style in persona {source_filename or 'unknown'}; falling back to simple parser."
            )
            style_lines = [line for line in style_text.split("\n") if line.strip()]
            for line in style_lines:
                m = re.match(r"^\s*([^:]+):\s*(.*)$", line)
                if m:
                    style[m.group(1).strip()] = m.group(2).strip()

    # If id missing, fall back to filename-derived id
    if not pid and source_filename:
        pid = source_filename.lower().replace(" ", "_")

    if pid and display_name and system_prompt:
        return Persona(
            id=pid,
            display_name=display_name,
            emoji=emoji,
            description=description,
            system_prompt=system_prompt,
            style=style,
        )
    logging.debug("Persona file missing required fields: id/display_name/system_prompt")
    return None


def get_persona(persona_id: str, personas: Dict[str, Persona]) -> Persona | None:
    return personas.get(persona_id)


def list_personas(personas: Dict[str, Persona]) -> List[PersonaSummary]:
    return [
        PersonaSummary(id=p.id, display_name=p.display_name, description=p.description)
        for p in personas.values()
    ]
