# Claude Code + NoviSentinel

**One environment variable. Zero code changes.**

```bash
# Start NoviSentinel
docker run -d -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... ghcr.io/009-kumarji/novisentinel:latest

# Point Claude Code at it
export ANTHROPIC_BASE_URL=http://localhost:8000
claude
```

That's it. Every prompt you type goes through NoviSentinel first. Secrets and PII are
replaced with stable placeholders before the request reaches Anthropic. The response
is unredacted before it reaches you.

---

## Verify it's working

In a new terminal while NoviSentinel is running:

```bash
curl http://localhost:8000/v1/messages \
  -H "x-api-key: anything" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 64,
    "messages": [{
      "role": "user",
      "content": "My AWS key is AKIAIOSFODNN7EXAMPLE. What should I do?"
    }]
  }'
```

Check the NoviSentinel logs (`docker logs <container>`). You'll see the upstream request
contained `<REDACTED_AWS_SECRET_KEY_001>`, not the actual key.

---

## Persistent setup (shell profile)

Add to `~/.bashrc` or `~/.zshrc` to have it apply automatically:

```bash
# Start NoviSentinel on login (only if Docker is running)
if docker info &>/dev/null 2>&1; then
  docker start novisentinel 2>/dev/null || \
    docker run -d --name novisentinel -p 8000:8000 \
      -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
      ghcr.io/009-kumarji/novisentinel:latest
  export ANTHROPIC_BASE_URL=http://localhost:8000
fi
```

---

## What's proxied

| What you send | What Anthropic sees |
|---------------|---------------------|
| `AKIAIOSFODNN7EXAMPLE` | `<REDACTED_AWS_SECRET_KEY_001>` |
| `john@example.com` | `<REDACTED_EMAIL_ADDRESS_001>` |
| `sk-ant-api03-xxxx` | `<REDACTED_API_KEY_001>` |
| `192.168.1.1` | `<REDACTED_IP_ONLY_001>` |
| "ignore previous instructions" | **blocked — 400 returned** |
