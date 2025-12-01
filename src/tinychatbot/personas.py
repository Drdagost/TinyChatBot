from dataclasses import dataclass
from typing import Dict, List, Any
from pathlib import Path

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
    personas = {}
    personas_path = Path(personas_dir)
    if not personas_path.is_dir():
        return personas
    
    for md_file in personas_path.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            persona = parse_persona(content)
            if persona:
                personas[persona.id] = persona
        except Exception as e:
            print(f"Error loading persona {md_file}: {e}")
    return personas

def parse_persona(content: str) -> Persona | None:
    sections = {}
    current_section = None
    lines = content.split('\n')
    for line in lines:
        if line.strip().startswith('[') and line.strip().endswith(']'):
            current_section = line.strip()[1:-1]
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(line)
    
    meta = '\n'.join(sections.get('meta', [])).strip()
    system_prompt = '\n'.join(sections.get('system_prompt', [])).strip()
    style_text = '\n'.join(sections.get('style', [])).strip()
    
    # Parse meta
    meta_lines = meta.split('\n')
    meta_dict = {}
    for line in meta_lines:
        if ':' in line:
            key, value = line.split(':', 1)
            meta_dict[key.strip()] = value.strip()
    
    id = meta_dict.get('id')
    display_name = meta_dict.get('display_name')
    emoji = meta_dict.get('emoji', '')
    description = meta_dict.get('description', '')
    
    # Parse style
    style = {}
    style_lines = style_text.split('\n')
    for line in style_lines:
        if ':' in line:
            key, value = line.split(':', 1)
            style[key.strip()] = value.strip()
    
    if id and display_name and system_prompt:
        return Persona(id=id, display_name=display_name, emoji=emoji, description=description, system_prompt=system_prompt, style=style)
    return None

def get_persona(persona_id: str, personas: Dict[str, Persona]) -> Persona | None:
    return personas.get(persona_id)

def list_personas(personas: Dict[str, Persona]) -> List[PersonaSummary]:
    return [PersonaSummary(id=p.id, display_name=p.display_name, description=p.description) for p in personas.values()]