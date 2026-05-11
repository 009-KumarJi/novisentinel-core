# Examples

Minimal, copy-pasteable examples showing how to integrate NoviSentinel with each major LLM provider and framework. Pick one, copy it, swap in your keys, and run.

## Common setup

```bash
# 1. Start the API
docker compose up -d

# 2. Install the SDK
pip install novisentinel

# 3. Set env vars
export NOVISENTINEL_API_KEY=dev-master-key   # or your real key
export NOVISENTINEL_URL=http://localhost:8000
```

## Examples

| Example | What it shows |
|---------|--------------|
| [`openai_wrapper.py`](openai_wrapper.py) | Scan input + output around `openai.chat.completions.create()` |
| [`anthropic_wrapper.py`](anthropic_wrapper.py) | Same for the Anthropic SDK |
| [`langchain_callback.py`](langchain_callback.py) | `NoviSentinelCallbackHandler` for any LangChain LLM |
| [`streamlit_chat.py`](streamlit_chat.py) | A 60-line Streamlit chat UI with NoviSentinel on both directions |
| [`ollama_proxy.md`](ollama_proxy.md) | Using the OpenAI example with Ollama / LM Studio |
| [`fastapi_middleware.py`](fastapi_middleware.py) | Drop-in scanner middleware for FastAPI apps |
| [`flask_middleware.py`](flask_middleware.py) | Same for Flask |

## Running an example

```bash
cd examples
pip install -r requirements.txt
python openai_wrapper.py
```
