import pytest
from tinychatbot.app import ContentAgent
from tinychatbot.personas import Persona


def test_set_persona_valid_and_invalid():
    agent = ContentAgent.__new__(ContentAgent)
    # prepare minimal attributes used by set_persona
    mock_persona = Persona(
        id="default",
        display_name="Default",
        emoji="🤖",
        description="desc",
        system_prompt="You are default.",
        style={},
    )
    agent.persona_store = {"default": mock_persona}
    agent.persona_id = "default"

    # valid set
    agent.set_persona("default")
    assert agent.persona_id == "default"

    # invalid set should raise ValueError
    with pytest.raises(ValueError):
        agent.set_persona("nonexistent")


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
