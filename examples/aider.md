# Aider + NoviSentinel

```bash
# Start NoviSentinel
docker run -d -p 8000:8000 -e OPENAI_API_KEY=sk-... ghcr.io/009-kumarji/novisentinel:latest

# Run aider through it
aider --openai-api-base http://localhost:8000/v1

# Or with Anthropic models
docker run -d -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... ghcr.io/009-kumarji/novisentinel:latest
aider --model claude-3-5-sonnet-20241022 \
      --anthropic-api-base-url http://localhost:8000
```

Aider reads your codebase and sends file contents with every prompt. NoviSentinel
strips API keys, secrets, and PII from those payloads before they reach the model.
