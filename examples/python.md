# Python SDK + NoviSentinel

## anthropic SDK

```python
from anthropic import Anthropic

client = Anthropic(
    base_url="http://localhost:8000",
    api_key="anything",  # NoviSentinel uses ANTHROPIC_API_KEY from its own env
)

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "My AWS key is AKIAIOSFODNN7EXAMPLE. Is it valid?"}
    ],
)
print(message.content[0].text)
# The key was redacted before leaving your machine.
# Claude's response references <REDACTED_AWS_SECRET_KEY_001>.
# NoviSentinel restores it to AKIAIOSFODNN7EXAMPLE before returning to you.
```

## openai SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="anything",
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "Check if my DB password 'hunter2' is in the code."}
    ],
)
print(response.choices[0].message.content)
```

## Streaming

Both SDKs' streaming APIs work exactly the same way — NoviSentinel handles
SSE streaming and restores placeholders in the stream chunks transparently.

```python
with client.messages.stream(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Explain my API key AKIAIOSFODNN7EXAMPLE"}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```
