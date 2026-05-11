# Using NoviSentinel with Ollama / LM Studio

Ollama and LM Studio both expose an OpenAI-compatible API. The `openai_wrapper.py`
example works as-is — just point the OpenAI client at your local Ollama instance.

## Ollama

```python
from openai import OpenAI
from novisentinel import Client
import os

# Point the OpenAI client at Ollama's OpenAI-compatible endpoint
openai_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # required by the client but unused by Ollama
)

sentinel = Client(
    api_key=os.environ.get("NOVISENTINEL_API_KEY", "dev-master-key"),
    base_url=os.environ.get("NOVISENTINEL_URL", "http://localhost:8000"),
)

def safe_chat(user_message: str, model: str = "llama3.2") -> str:
    input_scan = sentinel.scan(user_message, context="input")
    if input_scan.action == "block":
        return f"[blocked: {input_scan.detections[0].type}]"

    resp = openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": input_scan.redacted_text}],
    )
    reply = resp.choices[0].message.content or ""

    output_scan = sentinel.scan(reply, context="output")
    return "[blocked]" if output_scan.action == "block" else output_scan.redacted_text
```

## LM Studio

Same pattern, different port (LM Studio default: `1234`):

```python
openai_client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
)
```

## Known differences vs. the OpenAI API

| Feature | OpenAI | Ollama / LM Studio |
|---------|--------|--------------------|
| Tool calling | Full support | Model-dependent |
| Streaming | Yes | Yes |
| Model names | `gpt-4o-mini` etc. | Local model names (`llama3.2`, `mistral`, …) |
| Vision | Some models | Model-dependent |

For full compatibility, use `openai_wrapper.py` unchanged and just swap `base_url`
and `api_key`. The NoviSentinel scan layer is provider-agnostic.
