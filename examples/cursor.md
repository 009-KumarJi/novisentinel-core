# Cursor + NoviSentinel

## OpenAI models (GPT-4o, etc.)

1. Start NoviSentinel with your OpenAI key:
   ```bash
   docker run -d -p 8000:8000 -e OPENAI_API_KEY=sk-... ghcr.io/009-kumarji/novisentinel:latest
   ```

2. In Cursor: **Settings → Models → Override OpenAI Base URL**
   ```
   http://localhost:8000/v1
   ```

3. Leave your OpenAI API key in Cursor settings as-is (NoviSentinel ignores it for routing;
   it uses the key you passed to the container).

---

## Anthropic models (Claude)

1. Start NoviSentinel with your Anthropic key:
   ```bash
   docker run -d -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... ghcr.io/009-kumarji/novisentinel:latest
   ```

2. In Cursor: **Settings → Models → Add Model** → select Anthropic provider →
   set **API Base URL** to `http://localhost:8000`.

---

## What's proxied

Cursor sends every file context, diff, and inline completion through the same API call
your prompt goes through. All of those pass through NoviSentinel's detectors. Your
credentials in `.env`, your customer data in test fixtures, your internal hostnames — all
replaced with stable placeholders before they leave your machine.
