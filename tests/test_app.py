import pytest
from unittest.mock import patch, MagicMock
from tinychatbot.app import ContentAgent


def test_content_agent_init_valid(monkeypatch):
    """Test ContentAgent initialization with valid content directory and mocked dependencies."""
    # Mock environment variables
    with patch('os.getenv') as mock_getenv:
        mock_getenv.side_effect = lambda key, default=None: {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "fake_key",
            "VECTOR_PROVIDER": "faiss",
            "CONTENT_DIR": "content"
        }.get(key, default)
        
        # Mock load_documents to return sample documents
        with patch('tinychatbot.app.load_documents') as mock_load:
            mock_load.return_value = [
                {'path': 'content/test1.txt', 'text': 'This is test content 1.'},
                {'path': 'content/test2.txt', 'text': 'This is test content 2.'}
            ]
            
            agent = ContentAgent(content_dir='content')
            
            assert agent.content_dir == 'content'
            assert len(agent.docs) == 2
            assert 'content/test1.txt' in agent.docs
            assert agent.docs['content/test1.txt'] == 'This is test content 1.'


def test_content_agent_init_missing_content_dir(monkeypatch):
    """Test ContentAgent raises FileNotFoundError for missing content directory."""
    with patch('os.getenv') as mock_getenv:
        mock_getenv.side_effect = lambda key, default=None: {
            "OPENAI_API_KEY": "fake_key",
            "LLM_PROVIDER": "openai",
            "VECTOR_PROVIDER": "faiss",
            "CONTENT_DIR": "content"
        }.get(key, default)
        
        with pytest.raises(FileNotFoundError, match="Content directory 'nonexistent' not found"):
            ContentAgent(content_dir='nonexistent')


def test_content_agent_init_missing_api_key(monkeypatch):
    """Test ContentAgent exits for missing API key."""
    with patch('os.getenv') as mock_getenv:
        mock_getenv.side_effect = lambda key, default=None: {
            "LLM_PROVIDER": "openai",
            "VECTOR_PROVIDER": "faiss",
            "CONTENT_DIR": "content"
        }.get(key, default)
        
        with patch('sys.exit') as mock_exit:
            ContentAgent(content_dir='content')
            mock_exit.assert_called_once_with(1)


def test_system_prompt():
    """Test system prompt generation."""
    from tinychatbot.personas import Persona
    
    agent = ContentAgent.__new__(ContentAgent)  # Create instance without __init__
    agent.docs = {
        'content/doc1.txt': 'Content of document 1.',
        'content/doc2.txt': 'Content of document 2.'
    }
    agent.content_dir = 'content'
    
    # Mock persona store
    mock_persona = Persona(
        id='default',
        display_name='Default Assistant',
        emoji='🤖',
        description='Standard assistant behavior',
        system_prompt='You are a helpful assistant.',
        style={}
    )
    agent.persona_store = {'default': mock_persona}
    agent.persona_id = 'default'
    
    prompt = agent.system_prompt()
    
    assert "subject-matter expert" in prompt
    assert "doc1.txt" in prompt
    assert "doc2.txt" in prompt
    assert "Content of document 1." in prompt
    assert "You are a helpful assistant." in prompt


def test_handle_tool_call():
    """Test handling of tool calls."""
    agent = ContentAgent.__new__(ContentAgent)
    
    # Mock tool call for record_unknown_question
    tool_call = MagicMock()
    tool_call.function.name = 'record_unknown_question'
    tool_call.function.arguments = '{"question": "Unknown question"}'
    tool_call.id = 'test_id'
    
    with patch('tinychatbot.app.record_unknown_question') as mock_record:
        mock_record.return_value = {"recorded": "ok"}
        
        results = agent.handle_tool_call([tool_call])
        
        assert len(results) == 1
        assert results[0]['role'] == 'tool'
        assert results[0]['content'] == '{"recorded": "ok"}'
        assert results[0]['tool_call_id'] == 'test_id'
        mock_record.assert_called_once_with(question="Unknown question")


def test_chat_no_tool_calls(monkeypatch):
    """Test chat method without tool calls."""
    # Mock OpenAI
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is a test answer."
    mock_response.choices[0].finish_reason = "stop"
    mock_client.chat.completions.create.return_value = mock_response
    
    agent = ContentAgent.__new__(ContentAgent)
    agent.openai = mock_client
    agent.system_prompt = MagicMock(return_value="System prompt")
    
    with patch('tinychatbot.config.Config') as mock_config:
        mock_config.LLM_MODEL = "gpt-3.5-turbo"
        
        answer = agent.chat("Test question", [{"role": "user", "content": "Previous message"}])
        
        assert answer == "This is a test answer."
        mock_client.chat.completions.create.assert_called_once()


def test_chat_with_tool_calls(monkeypatch):
    """Test chat method with tool calls."""
    # Mock OpenAI for initial call with tool
    mock_client = MagicMock()
    mock_tool_response = MagicMock()
    mock_tool_response.choices[0].message.tool_calls = [MagicMock()]
    mock_tool_response.choices[0].message.tool_calls[0].function.name = 'record_unknown_question'
    mock_tool_response.choices[0].message.tool_calls[0].function.arguments = '{"question": "Unknown"}'
    mock_tool_response.choices[0].message.tool_calls[0].id = 'tool_id'
    mock_tool_response.choices[0].finish_reason = "tool_calls"
    
    # Second call without tool
    mock_final_response = MagicMock()
    mock_final_response.choices[0].message.content = "Final answer."
    mock_final_response.choices[0].finish_reason = "stop"
    
    mock_client.chat.completions.create.side_effect = [mock_tool_response, mock_final_response]
    
    agent = ContentAgent.__new__(ContentAgent)
    agent.openai = mock_client
    agent.system_prompt = MagicMock(return_value="System prompt")
    agent.handle_tool_call = MagicMock(return_value=[{"role": "tool", "content": "{}", "tool_call_id": "tool_id"}])
    
    with patch('tinychatbot.config.Config') as mock_config:
        mock_config.LLM_MODEL = "gpt-3.5-turbo"
        
        answer = agent.chat("Test question", [])
        
        assert answer == "Final answer."
        assert mock_client.chat.completions.create.call_count == 2