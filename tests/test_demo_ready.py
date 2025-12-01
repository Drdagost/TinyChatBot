from unittest.mock import MagicMock
from tinychatbot.personas import Persona
from tinychatbot.app import ContentAgent


def make_response(content="ok"):
    mock_response = MagicMock()
    # structure used in ContentAgent.chat: response.choices[0].message.content
    choice = MagicMock()
    choice.message.content = content
    choice.finish_reason = "stop"
    mock_response.choices = [choice]
    return mock_response


def test_persona_switch_updates_system_prompt():
    agent = ContentAgent.__new__(ContentAgent)
    # minimal attributes
    agent.docs = {'content/doc1.txt': 'doc text'}
    agent.content_dir = 'content'

    persona_a = Persona(id='a', display_name='A', emoji='', description='', system_prompt='Persona A instructions', style={})
    persona_b = Persona(id='b', display_name='B', emoji='', description='', system_prompt='Persona B instructions', style={})

    agent.persona_store = {'a': persona_a, 'b': persona_b}
    agent.persona_id = 'a'

    # mock openai client
    recorded_calls = []

    def fake_create(*args, **kwargs):
        # record messages for assertion
        recorded_calls.append(kwargs.get('messages') or (args[1] if len(args) > 1 else None))
        return make_response("first")

    mock_openai = MagicMock()
    mock_openai.chat.completions.create.side_effect = fake_create
    agent.openai = mock_openai

    # first chat uses persona A
    res1 = agent.chat("q1", [])
    assert res1 == "first"
    assert len(recorded_calls) == 1
    sys_msg = recorded_calls[0][0]
    assert 'Persona A instructions' in sys_msg['content']

    # switch persona to B and chat again
    recorded_calls.clear()
    # update side effect to return second response
    def fake_create2(*args, **kwargs):
        recorded_calls.append(kwargs.get('messages') or (args[1] if len(args) > 1 else None))
        return make_response("second")

    mock_openai.chat.completions.create.side_effect = fake_create2
    agent.set_persona('b')
    res2 = agent.chat("q2", [])
    assert res2 == "second"
    assert len(recorded_calls) == 1
    sys_msg2 = recorded_calls[0][0]
    assert 'Persona B instructions' in sys_msg2['content']


def test_no_personas_system_prompt_has_guardrail():
    agent = ContentAgent.__new__(ContentAgent)
    agent.docs = {'content/doc1.txt': 'doc text'}
    agent.content_dir = 'content'
    agent.persona_store = {}
    agent.persona_id = 'default'

    prompt = agent.system_prompt()
    assert 'IMPORTANT: Persona instructions only affect tone and style' in prompt
    # Should not include a 'Persona instructions' section
    assert 'Persona instructions:' not in prompt
