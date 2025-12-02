import json
import os
from typing import Any, Optional, Type

import gradio as gr
import requests
from dotenv import load_dotenv
from loguru import logger

from . import qa_service as qs
from .documents import load_documents
from .personas import Persona, load_personas

load_dotenv(override=True)


def record_unknown_question(question):
    """Lightweight recorder for questions outside the provided content scope.
    This prints to stdout and optionally uses Pushover if PUSHOVER_* env vars are set.
    """
    print(f"[record_unknown_question] {question}", flush=True)
    logger.info(f"[record_unknown_question] {question}")
    if os.getenv("PUSHOVER_TOKEN") and os.getenv("PUSHOVER_USER"):
        try:
            requests.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": os.getenv("PUSHOVER_TOKEN"),
                    "user": os.getenv("PUSHOVER_USER"),
                    "message": f"Unknown question: {question}",
                },
                timeout=5,
            )
        except Exception:
            pass
    return {"recorded": "ok"}


record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Record a question that couldn't be answered from the available documents",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered",
            },
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}

tools = [{"type": "function", "function": record_unknown_question_json}]


class ContentAgent:
    """Reads a folder of documents and answers questions as a subject-matter expert on that content.

    Behavior:
    - Loads text from PDFs and text/markdown files under CONTENT_DIR (env) or 'content' by default.
    - Requires the content directory to exist.
    - System prompt instructs the model to act as an SME.
    """

    def __init__(
        self,
        content_dir: str | None = None,
        persona_store: dict[str, Persona] | None = None,
        default_persona_id: str = "default",
        openai_client: object | None = None,
    ):
        # Load environment variables early
        from dotenv import load_dotenv

        load_dotenv(override=True)

        # Get provider settings
        llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        vector_provider = os.getenv(
            "VECTOR_PROVIDER", os.getenv("VECTOR_DB", "faiss")
        ).lower()

        # Check required keys based on LLM provider
        if llm_provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError(
                    "OPENAI_API_KEY is required for LLM_PROVIDER=openai. Please set it in your .env file."
                )
        elif llm_provider == "azure":
            if not os.getenv("OPENAI_API_KEY") or not os.getenv(
                "AZURE_OPENAI_DEPLOYMENT"
            ):
                raise RuntimeError(
                    "OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT are required for LLM_PROVIDER=azure. Please set them in your .env file."
                )
        elif llm_provider == "huggingface":
            if not os.getenv("HUGGINGFACE_API_KEY"):
                raise RuntimeError(
                    "HUGGINGFACE_API_KEY is required for LLM_PROVIDER=huggingface. Please set it in your .env file."
                )
        elif llm_provider == "openrouter":
            if not os.getenv("OPENROUTER_API_KEY"):
                raise RuntimeError(
                    "OPENROUTER_API_KEY is required for LLM_PROVIDER=openrouter. Please set it in your .env file."
                )
        elif llm_provider == "anthropic":
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is required for LLM_PROVIDER=anthropic. Please set it in your .env file."
                )
        elif llm_provider == "google":
            if not os.getenv("GOOGLE_API_KEY"):
                raise RuntimeError(
                    "GOOGLE_API_KEY is required for LLM_PROVIDER=google. Please set it in your .env file."
                )
        elif llm_provider == "deepseek":
            if not os.getenv("DEEPSEEK_API_KEY"):
                raise RuntimeError(
                    "DEEPSEEK_API_KEY is required for LLM_PROVIDER=deepseek. Please set it in your .env file."
                )
        elif llm_provider == "ollama":
            pass  # no key needed

        # Check required keys based on vector provider
        if vector_provider == "pinecone":
            if not os.getenv("PINECONE_API_KEY") or not os.getenv("PINECONE_ENV"):
                raise RuntimeError(
                    "PINECONE_API_KEY and PINECONE_ENV are required for VECTOR_PROVIDER=pinecone. Please set them in your .env file."
                )
        # For faiss, chroma, memory, no additional keys needed

        self.persona_store: dict[str, Persona] = persona_store or {}
        self.persona_id: str = default_persona_id

        # Allow injection of a pre-configured OpenAI client (useful for tests)
        # and lazily import the real OpenAI client class so importing this
        # module doesn't require the `openai` library to be installed.
        self.openai: Optional[Any] = openai_client

        # Prepare a local placeholder for the imported OpenAI class. We
        # initialize it to None with an explicit Optional type so mypy won't
        # complain when we assign the imported class or None below.
        _OpenAIClass: Optional[Type[Any]] = None
        try:
            from openai import OpenAI as _ImportedOpenAI  # type: ignore

            _OpenAIClass = _ImportedOpenAI
        except Exception:
            _OpenAIClass = None

        # Store the OpenAI class (or None if package not available) so we can
        # instantiate it later when an API key is present.
        self._openai_class = _OpenAIClass
        # Ensure static type is `str` so mypy knows this is safe to pass to os.path.isdir
        self.content_dir: str = str(content_dir or os.getenv("CONTENT_DIR", "content"))
        if not os.path.isdir(self.content_dir):
            # Do not fall back to legacy 'me' folder — require an explicit content directory.
            raise FileNotFoundError(
                f"Content directory '{self.content_dir}' not found."
            )

        self.docs = self._load_documents(self.content_dir)

    def set_persona(self, persona_id: str):
        if persona_id in self.persona_store:
            self.persona_id = persona_id
        else:
            raise ValueError(f"Persona {persona_id} not found")

    def _load_documents(self, folder_path: str) -> dict:
        """Walk the folder and extract text from known file types. Returns a dict[path] = text."""
        docs = load_documents(folder_path)
        if not docs:
            logger.warning(f"No readable documents found under '{folder_path}'")
        return {d["path"]: d["text"] for d in docs}

    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            logger.info(f"Tool called: {tool_name}")
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append(
                {
                    "role": "tool",
                    "content": json.dumps(result),
                    "tool_call_id": tool_call.id,
                }
            )
        return results

    def system_prompt(self) -> str:
        """Build a system prompt that instructs the model to act as an SME using only the provided documents."""
        prompt_lines = [
            "You are a helpful, accurate subject-matter expert. Answer user questions using ONLY the information contained in the provided documents.",
            "Do not impersonate any person. If the answer is not contained in the documents, say you don't know and offer to record the question.",
            "Be concise, factual, and cite which document (filename) you used when giving facts if appropriate.",
            "",
        ]

        # Guardrail: persona instructions should NOT override the SME constraints above.
        # This explicit line helps prevent persona authors from accidentally weakening
        # the requirement to answer only from provided documents.
        prompt_lines.append(
            "IMPORTANT: Persona instructions only affect tone and style. They must NOT change your requirement to answer ONLY from the provided documents or to avoid guessing."
        )
        prompt_lines.append("")

        # Add persona instructions (style/tone)
        persona = self.persona_store.get(self.persona_id)
        if persona:
            prompt_lines.append("Persona instructions:")
            prompt_lines.append(persona.system_prompt)
            prompt_lines.append("")

        prompt_lines.append(
            "The documents available are listed below (filename followed by an excerpt):"
        )
        prompt_lines.append("")

        for path, text in self.docs.items():
            # increase preview window so multi-page documents are more likely to be included
            safe_preview = text[:5000].replace("\n", " ")
            prompt_lines.append(f"--- {os.path.relpath(path, self.content_dir)} ---")
            prompt_lines.append(safe_preview)
            prompt_lines.append("")

        return "\n".join(prompt_lines)

    def chat(self, message, history):
        messages = (
            [{"role": "system", "content": self.system_prompt()}]
            + history
            + [{"role": "user", "content": message}]
        )
        # Ensure an OpenAI client is available if the selected LLM provider needs it.
        if self.openai is None:
            llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
            if llm_provider == "openai":
                if not os.getenv("OPENAI_API_KEY"):
                    raise RuntimeError(
                        "OPENAI_API_KEY is required for LLM_PROVIDER=openai"
                    )
                if not getattr(self, "_openai_class", None):
                    raise RuntimeError("openai package is not installed")
                # pass the api_key explicitly to avoid the library reading env in unexpected ways
                self.openai = self._openai_class(api_key=os.getenv("OPENAI_API_KEY"))
        done = False
        while not done:
            from .config import Config

            response = self.openai.chat.completions.create(
                model=Config.LLM_MODEL, messages=messages, tools=tools
            )
            if response.choices[0].finish_reason == "tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)
            else:
                done = True

        return response.choices[0].message.content


def chat_with_citations(agent: ContentAgent, message: str, history: list):
    """Wrapper used by the UI: get the agent's textual reply and then augment it with
    structured source metadata from the QA service so the UI can render page/paragraph citations.
    """
    # Get plain text answer from the agent
    answer = agent.chat(message, history)

    # Use the qa_service path to get structured sources for the same question
    try:
        req = qs.QARequest(question=message, top_k=5)
        qa_resp = qs.qa(req)
        sources = qa_resp.get("sources", [])
    except Exception:
        sources = []

    if sources:
        # Format citations: show filename plus page/para when available
        citation_lines = ["\n\nCitations:"]
        for s in sources:
            src = s.get("source", "unknown")
            parts = [
                os.path.relpath(src, agent.content_dir)
                if agent.content_dir and src.startswith(agent.content_dir)
                else src
            ]
            if "page" in s:
                parts.append(f"page:{s['page']}")
            if "para" in s:
                parts.append(f"para:{s['para']}")
            citation_lines.append(" - " + ", ".join(parts))
        answer = answer + "\n" + "\n".join(citation_lines)

    return answer


def main():
    """Entrypoint for running the app. This allows tools like `uv run app` to import
    the `app` module and call `main()`.
    """
    from .config import Config

    persona_store = load_personas(Config.PERSONAS_DIR)
    default_persona_id = Config.DEFAULT_PERSONA_ID
    agent = ContentAgent(
        content_dir=Config.CONTENT_DIR,
        persona_store=persona_store,
        default_persona_id=default_persona_id,
    )

    # Persona options for dropdown (show friendly labels, return persona id via mapping)
    # persona_label_map: id -> "DisplayName emoji"
    persona_label_map = {
        p.id: f"{p.display_name} {p.emoji}" for p in persona_store.values()
    }
    # reverse map: label -> id (used when dropdown returns the label)
    label_to_id = {label: pid for pid, label in persona_label_map.items()}
    persona_label_choices = list(label_to_id.keys())

    # Log loaded personas for operator visibility
    if persona_label_map:
        logger.info(f"Loaded personas: {persona_label_map}")
        print("Loaded personas:")
        for pid, label in persona_label_map.items():
            print(f" - {pid}: {label}")
    else:
        logger.warning(
            "No personas found in PERSONAS_DIR; running without persona styles."
        )

    def chat_with_persona(msg, hist, persona_label):
        # Dropdown returns a label like "DisplayName emoji"; map it to the persona id.
        persona_id = label_to_id.get(persona_label, default_persona_id)
        try:
            agent.set_persona(persona_id)
        except Exception:
            print(
                f"Requested persona '{persona_id}' not available; falling back to '{default_persona_id}'"
            )
            try:
                agent.set_persona(default_persona_id)
            except Exception:
                pass
        return chat_with_citations(agent, msg, hist)

    # Use wrapper so UI shows page/paragraph citations when available
    # Present friendly labels in the dropdown but return the selected label; we map back to id.
    default_label = persona_label_map.get(default_persona_id, None)
    gr.ChatInterface(
        fn=chat_with_persona,
        additional_inputs=[
            gr.Dropdown(
                choices=persona_label_choices, label="Persona", value=default_label
            )
        ],
    ).launch()


if __name__ == "__main__":
    main()
