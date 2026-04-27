---
name: model-config-evidence-gate
description: Verify model availability/retirement with current authoritative sources before changing model configuration; require evidence and recency.
version: 1.0.0
author: Hermes Agent
---

# Model Config Evidence Gate

## When to use
- Any change to model IDs in config (e.g., `gpt-*`, `*-codex`, fallback models, provider defaults).
- Any claim that a model is retired/renamed/available.

## Core rule
Do **not** change model config from assumption or memory.
Require current evidence from authoritative sources first.

## Required evidence checklist
1. At least one official model-status source (e.g., OpenAI Help release notes).
2. At least one plan/availability source if subscription impact matters (pricing/help article).
3. At least one **live surface catalog** source for the surface being configured (e.g., `codex debug models` for OpenAI Codex CLI-backed menus).
4. Recency check (use latest update date in source, not old cached belief).
5. Explicit mapping in notes: `model -> status (active/renamed/retired)`.
6. Surface mapping in notes: `ChatGPT picker vs Codex catalog vs API availability` (avoid cross-surface assumptions).

## Retrieval workflow
1. Fetch official links.
2. If direct fetch is blocked (403/anti-bot), retry via text mirror (`r.jina.ai/http://...`) and record this fallback.
3. Query live surface catalog for the exact runtime path being changed (example: `codex debug models` for `/model` options in Codex-backed Telegram/CLI).
4. Extract exact lines/snippets mentioning the target model and status.
5. If sources disagree, rank by freshness and surface relevance:
   - runtime catalog for the actual surface > official release notes/pricing > third-party news.
6. Only then patch config.
7. Re-read config to confirm exact final values.
8. Run a smoke check on the affected path/tool.
9. If UI/menu output still shows old options, log it as cache/catalog staleness and do not claim rollout complete until menu reflects the new set.

## Output contract
Before applying change, report:
- sources used
- model status conclusion with quote snippets
- why target model is chosen

After applying change, report:
- file + keys changed
- verification readback
- smoke-test result

## Codex `/model` picker drift guard (important)
When auditing `/model` for `openai-codex`, explicitly verify whether UI options come from:
- static curated list (e.g., in `hermes_cli/model_switch.py`), or
- live catalog fetch (e.g., `get_codex_model_ids(access_token)`).

If static list is used, treat it as drift-prone by default.

Required drift check:
1. Capture picker list as currently rendered by runtime path.
2. Capture live catalog with the same credentials/session.
3. Compute exact diff:
   - `new_in_live` (should be added to picker)
   - `missing_from_live` (candidates to hide/deprecate)
4. Do not claim fix complete until UI picker reflects the post-fix live set.

Preferred remediation pattern:
- live-first source for picker
- selection/validation path must use the SAME live catalog source as the picker (same runtime credentials/session), not a tokenless fallback path
- safe fallback to static list when live fetch fails
- tests for: new model appears, retired/missing model no longer shown, live-fetch failure fallback behavior, and picker-visible model successfully validates when selected

## WSL / cross-home credential discovery guard
When provider visibility depends on local credential files (for example Claude Code OAuth in `~/.claude/.credentials.json`), verify discovery on the actual runtime home used by Hermes. In WSL setups, credentials may exist only on the Windows side (for example `/mnt/c/Users/<user>/.claude/.credentials.json`) while `Path.home()` inside WSL has no copy.

Required check for provider-picker regressions:
1. Probe the WSL home path actually read by the code.
2. Probe likely mounted Windows fallback path(s) when the product is expected to interoperate with host-installed tools.
3. Confirm whether provider discovery intentionally supports only WSL-local files or should also support mounted-host credentials.
4. Add a regression test for the chosen behavior so providers do not silently disappear from the picker.

## Hermes implementation notes (openai-codex)
When applying this in Hermes Agent:
- Picker source path: `hermes_cli/model_switch.py` in `list_authenticated_providers()` overlay section.
- Drift origin: default behavior uses curated static lists (`_PROVIDER_MODELS` / `DEFAULT_CODEX_MODELS`) which can lag live catalog.
- Live discovery call chain:
  1. `resolve_codex_runtime_credentials()` from `hermes_cli/auth.py`
  2. pass returned dict field `api_key` (not `access_token` attribute) into
  3. `get_codex_model_ids(access_token=...)` from `hermes_cli/codex_models.py`
- Failure handling: if live list is empty/throws, keep curated list as fallback to preserve availability.

## Verification add-on for model existence claims
For claims like "model X is usable now", require both:
1. Presence in live catalog (`get_codex_model_ids`).
2. A real invocation smoke test (example: `codex exec --model <id> ...`) with successful exit.
Do not conclude usability from catalog presence alone.

## Local custom-endpoint smoke test pattern (OpenAI-compatible + Ollama fallback)
When validating a new primary/fallback model pair in thClaws or a similar agent:
1. Verify the primary provider by calling the real client against a local OpenAI-compatible mock endpoint with `OPENAI_BASE_URL` and no `OPENAI_API_KEY`.
2. Use a mock that returns a real SSE/streaming response body for the exact wire format the client expects; a plain JSON-only response can falsely fail before the model logic is exercised.
3. If a simple `HTTPServer`-style mock produces transport/stream decode failures, switch to a raw socket mock that writes explicit `Content-Length` and SSE frames.
4. Verify the fallback provider separately with its own endpoint and model name, then confirm the application-level fallback order.
5. Re-read the exact config file after the patch (`.thclaws/settings.json` or equivalent) so the active primary model is proven, not just assumed.
6. Record the exact command and the expected stdout so later updates can rerun the same smoke test after upgrading the binary.

Example pattern:
- primary: `OPENAI_BASE_URL=http://127.0.0.1:<port>/v1/chat/completions` + no key
- fallback: `OLLAMA_BASE_URL=http://127.0.0.1:<port>` + `ollama/<model>`
- success criterion: the one-shot print command exits 0 and emits the mock assistant text

### thClaws-specific fallback verification
For thClaws releases that need `gpt-5.4-mini` as primary and `ollama/qwen3.5:cloud` as fallback:
1. Patch the runtime config to set the primary model explicitly.
2. Use a mock Ollama server that answers both `/api/version` and `/api/chat`.
3. Run the real CLI/REPL with `OPENAI_API_KEY` unset and `OLLAMA_BASE_URL` pointing to the mock.
4. Expect a startup line indicating OpenAI fallback and a final assistant response from the Ollama mock (for example, `hello from fallback ollama`).
5. Treat the flow as incomplete if startup falls back but the smoke test does not prove the final assistant output.

## Safety notes
- If evidence is conflicting or stale, do not proceed; hold and request newer source.
- Distinguish ChatGPT picker models vs Codex/API/surface-specific models; do not conflate names.

## Durable logging
For significant policy decisions, also:
- ingest a `hermes-learning note` summarizing evidence and decision rule
- add/update fact_store with the governance rule
- update memory preference if user requires this behavior consistently
