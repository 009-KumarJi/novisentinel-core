# Cline (VS Code) + NoviSentinel

1. Start NoviSentinel:
   ```bash
   docker run -d -p 8000:8000 -e OPENAI_API_KEY=sk-... ghcr.io/009-kumarji/novisentinel:latest
   ```

2. In VS Code, open Cline settings (the Cline sidebar → gear icon):
   - **API Provider**: `OpenAI Compatible`
   - **Base URL**: `http://localhost:8000/v1`
   - **API Key**: anything (Cline requires a non-empty value; NoviSentinel uses the key from the container env)
   - **Model**: `gpt-4o` (or whichever OpenAI model you want)

3. To use Claude via Cline:
   - Start NoviSentinel with `ANTHROPIC_API_KEY` instead
   - **API Provider**: `Anthropic`
   - **Base URL** (if Cline exposes it): `http://localhost:8000`

---

Cline reads workspace files and sends them with every tool call. NoviSentinel covers
all of that traffic — your `.env`, your test fixtures, your config files — before it
reaches the LLM.
