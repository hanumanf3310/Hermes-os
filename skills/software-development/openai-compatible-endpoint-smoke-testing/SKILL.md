---
name: openai-compatible-endpoint-smoke-testing
description: Validate keyless OpenAI-compatible endpoints with a local mock server, SSE streaming, and regression checks for clients like thClaws.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [testing, mocking, openai-compatible, sse, endpoint-validation, regression]
    related_skills: [systematic-debugging, test-driven-development, model-config-evidence-gate]
---

# OpenAI-Compatible Endpoint Smoke Testing

Use this when you need to prove that a client can talk to a custom OpenAI-compatible endpoint without an API key, and you want a reusable smoke-test pattern that survives future updates.

## When to use

- Verifying a custom `OPENAI_BASE_URL` / equivalent setting
- Checking keyless behavior against a local or private endpoint
- Confirming that a client really sends requests to the custom endpoint instead of the public OpenAI host
- Regression-testing provider routing or endpoint selection after code changes

## Key lesson

For streaming OpenAI chat clients, a plain JSON `200 OK` response is often *not* enough. If the client expects SSE streaming, the mock endpoint must speak SSE too.

If you see errors like:
- `stream: error decoding response body`
- request never reaches the mock handler
- the client retries without producing output

then the first thing to inspect is the mock transport shape, not the client logic.

## Workflow

### 1) Decide the exact contract

Record:
- target model name
- request path expected by the client
- whether the client sends `stream=true`
- whether auth should be absent or present
- whether `/v1/models` is queried before chat completion

For thClaws-style clients, the common contract is:
- `GET /v1/models`
- `POST /v1/chat/completions`
- `OPENAI_BASE_URL=http://host:port/v1/chat/completions`
- no `OPENAI_API_KEY` for the keyless path

### 2) Build a minimal mock server

Implement the smallest possible server that can prove the path works:

- `GET /v1/models`
  - return JSON like:
    ```json
    {"data":[{"id":"gpt-5.4-mini"}]}
    ```
- `POST /v1/chat/completions`
  - return `Content-Type: text/event-stream`
  - send at least one `data: {...}` chunk
  - include a terminal `data: [DONE]`
  - if the client consumes usage, include a final chunk with `usage`

Keep the server deterministic and log:
- request line
- request path
- presence/absence of `Authorization`

Always redact secrets in logs.

### 3) Run the client against the mock

Set the env vars explicitly:

```bash
env -u OPENAI_API_KEY \
OPENAI_BASE_URL=http://127.0.0.1:PORT/v1/chat/completions \
<client> --model <model> "hello"
```

Verify:
- exit code is 0
- output matches the mock response
- logs show the request reached the mock endpoint
- public OpenAI hosts were not contacted

### 4) If the request fails, debug the transport first

Check these before changing application code:

- Is the client using streaming?
- Did the mock return `text/event-stream`?
- Are SSE frames separated correctly (`\n\n` or `\r\n\r\n` consistently)?
- Did the mock include `data: [DONE]`?
- Did the mock close the connection cleanly?
- Did the request hit the right path, or did the client rewrite it?

A plain JSON response can look fine in curl and still fail in the client if the client expects SSE.

### 5) Add regression checks

Run targeted tests that prove the client kept the intended behavior:
- provider selection honors env vars
- status/help exposes user-configurable endpoints
- model routing still works after updates

Keep the smoke test in the same family as the regression checks so future updates do not silently break the keyless path.

## Practical thClaws pattern

For thClaws, the successful validation pattern was:

1. Mock `/v1/models`
2. Mock streaming `/v1/chat/completions` with SSE
3. Call:
   ```bash
   env -u OPENAI_API_KEY OPENAI_BASE_URL=http://127.0.0.1:18087/v1/chat/completions cargo run -q --bin thclaws-cli -- -p --model gpt-5.4-mini hello
   ```
4. Confirm stdout contains the expected response text
5. Confirm the mock logs show the request path and redacted auth header

## Common pitfalls

- Returning JSON instead of SSE for a streaming client
- Forgetting `data: [DONE]`
- Sending a response with the wrong path, such as `/v1/chat/completions` when the client expects `/v1/models` for discovery first
- Testing only the happy path without verifying request logs
- Assuming no-key behavior is broken when the real issue is transport framing

## What good looks like

A good smoke test proves all of these:
- the client reaches the custom endpoint
- no API key is required for that endpoint
- the response is parsed correctly
- future code changes can be caught with a small regression test
