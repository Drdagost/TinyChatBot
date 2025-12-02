from tinychatbot.personas import load_personas, parse_persona


def make_md(meta: str, system_prompt: str, style: str = "") -> str:
    return f"""
[meta]
{meta}

[system_prompt]
{system_prompt}

[style]
{style}
"""


def test_parse_persona_meta_colon_and_equal():
    content = """
[meta]
id: test_persona
display_name = Test Persona
emoji: 🤖
[system_prompt]
You are a test persona.
"""

    p = parse_persona(content, source_filename="test_persona")
    assert p is not None
    assert p.id == "test_persona"
    assert p.display_name == "Test Persona"
    assert "You are a test persona." in p.system_prompt


def test_parse_persona_missing_id_falls_back_to_filename():
    content = """
[meta]
display_name: Filename Persona
emoji: 🙂
[system_prompt]
Filename based persona prompt.
"""
    p = parse_persona(content, source_filename="filename_persona")
    assert p is not None
    assert p.id == "filename_persona"
    assert p.display_name == "Filename Persona"


def test_parse_persona_style_yaml_and_fallback():
    # YAML style when yaml is available; if not, fallback parser handles key: value
    content = """
[meta]
id: styled
display_name: Styled Persona
[system_prompt]
Styled persona here.
[style]
politeness: high
tone: friendly
"""
    p = parse_persona(content, source_filename="styled")
    assert p is not None
    assert p.style.get("politeness") == "high"
    assert p.style.get("tone") == "friendly"


def test_meta_parsing_colon_and_equal():
    md1 = make_md(
        "id: default\ndisplay_name: Default Assistant\nemoji: 🤖\ndescription: Default",
        "You are a helpful assistant.",
    )
    p1 = parse_persona(md1, source_filename="default")
    assert p1 is not None
    assert p1.id == "default"
    assert p1.display_name == "Default Assistant"

    md2 = make_md(
        "id = cheerful_support\ndisplay_name = Cheerful Support\nemoji = 😊\ndescription = Friendly",
        "You are cheerful.",
    )
    p2 = parse_persona(md2, source_filename="cheerful_support")
    assert p2 is not None
    assert p2.id == "cheerful_support"
    assert p2.display_name == "Cheerful Support"


def test_filename_fallback_when_id_missing():
    md = make_md(
        "display_name: NoId Persona\nemoji: 🧪\ndescription: Missing id",
        "I exist but have no id in meta.",
    )
    p = parse_persona(md, source_filename="fallback_name")
    assert p is not None
    assert p.id == "fallback_name"
    assert p.display_name == "NoId Persona"


def test_style_parsing_simple_key_values():
    style = "tone: upbeat\nemoji_usage: light\nformatting: bullet"
    md = make_md(
        "id: style_test\ndisplay_name: Style Test", "Style prompt.", style=style
    )
    p = parse_persona(md, source_filename="style_test")
    assert p is not None
    assert isinstance(p.style, dict)
    assert p.style.get("tone") == "upbeat"
    assert p.style.get("emoji_usage") == "light"


def test_load_personas_skips_duplicates(tmp_path, caplog):
    # create two files with same id
    content_a = make_md("id: dup\ndisplay_name: Dup A", "Prompt A")
    content_b = make_md("id: dup\ndisplay_name: Dup B", "Prompt B")

    fa = tmp_path / "a.md"
    fb = tmp_path / "b.md"
    fa.write_text(content_a, encoding="utf-8")
    fb.write_text(content_b, encoding="utf-8")

    caplog.clear()
    personas = load_personas(str(tmp_path))
    # Only one persona should be loaded for id 'dup'
    assert len([p for p in personas.keys() if p == "dup"]) == 1
    # Should log a warning about duplicate
    assert any("Duplicate persona id" in rec.message for rec in caplog.records)
