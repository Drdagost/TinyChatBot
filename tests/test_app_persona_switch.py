from unittest.mock import Mock

import pytest

from tinychatbot.app import ContentAgent
from tinychatbot.personas import Persona


def test_set_persona_valid_and_invalid(tmp_path):
    # create a minimal content dir so ContentAgent init succeeds
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "doc.txt").write_text("hello world")

    persona = Persona(
        id="p1",
        display_name="P1",
        emoji="🙂",
        description="desc",
        system_prompt="Be concise.",
        style={"tone": "brief"},
    )

    personas = {"p1": persona}

    fake_openai = Mock()
    agent = ContentAgent(
        content_dir=str(content_dir),
        persona_store=personas,
        default_persona_id="p1",
        openai_client=fake_openai,
    )

    # valid set_persona
    agent.set_persona("p1")
    assert agent.persona_id == "p1"
    # system prompt should include persona system prompt
    sp = agent.system_prompt()
    assert "Be concise." in sp

    # invalid persona should raise
    with pytest.raises(ValueError, match=r"Persona 'no-such' not found\. Available personas: \['p1'\]"):
        agent.set_persona("no-such")


def test_system_prompt_contains_guardrail_and_persona():
    agent = ContentAgent.__new__(ContentAgent)
    agent.persona_store = {}
    agent.persona_id = "default"
    agent.docs = {"content/doc1.txt": "Doc text"}
    agent.content_dir = "content"

    # set a persona and verify prompt includes guardrail and persona text
    p = Persona(
        id="p1",
        display_name="P1",
        emoji="",
        description="",
        system_prompt="Be playful.",
        style={},
    )
    agent.persona_store = {"p1": p}
    agent.persona_id = "p1"

    prompt = agent.system_prompt()
    assert "IMPORTANT: Persona instructions only affect tone and style" in prompt
    assert "Persona instructions:" in prompt
    assert "Be playful." in prompt
