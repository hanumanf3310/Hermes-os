# Telegram Model Picker Hardening Plan

> For Hermes: planning only. Do not implement from this document without explicit approval.

**Goal:** Fix the Telegram `/model` picker architecture so future model-catalog drift does not recur, `gpt-5.5`-style picker/validator mismatches cannot happen again, and Ollama Launch / Ollama Cloud model visibility remains consistent with the documented `ollama launch hermes` integration flow.

**Architecture summary:** Introduce a single authoritative picker-catalog service for each provider/surface, make selection validation consume the exact same resolved catalog snapshot used to render the picker, and add provider-specific discovery policies for `openai-codex`, `ollama-launch`, and `ollama-cloud`. The key change is architectural unification, not one-off patching.

**Outcomes required:**
1. If a model appears in Telegram picker, selecting it must not fail due to catalog mismatch.
2. Ollama Launch picker must always include the documented recommended cloud models, even if config also stores a smaller user subset.
3. Native `ollama-cloud` and `ollama-launch` must have explicit, separate semantics instead of accidentally shadowing each other.
4. Regressions must be blocked by dedicated cross-surface tests.

---

## 1. Current findings

### 1.1 OpenAI Codex mismatch
- Telegram picker provider list uses `list_authenticated_providers()`.
- For `openai-codex`, that code path already prefers live discovery using:
  - `resolve_codex_runtime_credentials()`
  - `get_codex_model_ids(access_token=token)`
- Result: picker shows live models including `gpt-5.5`.
- But selection validation later goes through `switch_model()` -> `validate_requested_model()` -> `provider_model_ids("openai-codex")`.
- `provider_model_ids("openai-codex")` currently calls `get_codex_model_ids()` **without** passing the runtime token.
- That falls back to local cache/default list and can reject a picker-visible model.

### 1.2 Ollama Launch recommended-model regression
- Docs at `https://docs.ollama.com/integrations/hermes#recommended-models` say `ollama launch hermes` should support cloud models automatically and list these recommended cloud models:
  - `kimi-k2.5:cloud`
  - `glm-5.1:cloud`
  - `qwen3.5:cloud`
  - `minimax-m2.7:cloud`
- Current picker behavior is dominated by config section `providers.ollama-launch`, which currently contains only two models in the user config.
- `list_authenticated_providers()` emits the config-backed `ollama-launch` row early, marks the slug as seen, and later skips the special `ollama-launch` fallback/augmentation path.
- Result: Telegram picker shows only the two config models instead of the documented recommended set.

## 2. Root-cause architecture problem

The current `/model` system mixes three different concepts without a shared contract:

1. **Render catalog** — models shown in picker UI
2. **Validation catalog** — models accepted when user selects/types one
3. **Provider discovery policy** — rules for whether a provider should appear at all

These are implemented in multiple places with overlapping but non-identical logic:
- `hermes_cli/model_switch.py`
- `hermes_cli/models.py`
- `gateway/run.py`
- `gateway/platforms/telegram.py`
- provider-specific helpers (`codex_models.py`, Anthropic adapter, Ollama cloud fetchers)

As long as these concerns remain split, future provider changes will keep producing drift bugs.

---

## 3. Proposed long-term design

## 3.1 Introduce a unified picker catalog layer
Create a provider-aware catalog builder that returns a normalized snapshot object for the active surface.

**New concept:** `ResolvedPickerCatalog`

Suggested fields:
- `provider_slug`
- `provider_label`
- `models`
- `total_models`
- `source`
- `validation_mode`
- `catalog_fingerprint`
- `metadata` (provider-specific context, e.g. token-backed/live/static/merged)

**Rules:**
- The picker UI renders from this object.
- The picker selection callback validates against this exact object, not by recomputing provider state differently.
- Text-command `/model <name>` may still do a fresh validation path, but for interactive picker it must use the same snapshot that rendered the buttons.

## 3.2 Add a selection contract for Telegram picker state
Extend Telegram picker state to store the resolved catalog snapshot per provider, not just a raw model list.

Current stored state:
- `providers`
- `selected_provider`
- `model_list`

Planned state:
- `providers` as resolved catalog entries
- per-provider snapshot metadata
- `catalog_fingerprint`
- optional validation policy enum

This ensures button click processing is deterministic and uses the same data the user actually saw.

## 3.3 Provider policy separation
Define explicit policy classes/helpers for:
- `openai-codex`
- `ollama-launch`
- `ollama-cloud`

### OpenAI Codex policy
- Picker source: live catalog via runtime credentials
- Validation source for picker selections: exact picker snapshot
- Validation source for text `/model gpt-5.5`: live catalog via same runtime credentials
- Fallback: cached/default only when live discovery truly unavailable
- Add explicit logging of which source was used (`live`, `cache`, `default`)

### Ollama Launch policy
Treat `ollama-launch` as a **documented integration mode**, not just a config-defined custom provider.

Rules:
- Always merge documented recommended cloud models into picker results for `ollama-launch`
- Then merge user-configured models from `providers.ollama-launch`
- Deduplicate, preserve stable priority ordering:
  1. current/default model first
  2. documented recommended cloud models next
  3. user-added extras after that
- This provider should not require `OLLAMA_API_KEY` for the documented `ollama launch hermes` flow
- Its semantics should be independent from native `ollama-cloud`

### Ollama Cloud policy
Treat `ollama-cloud` as native provider mode.

Rules:
- Credential-gated via `OLLAMA_API_KEY` or equivalent official authenticated runtime source if later added
- Uses `fetch_ollama_cloud_models()` / live API / models.dev merge
- Does not override or shadow `ollama-launch`

## 4. Implementation phases

## Phase 1 — Catalog contract and tests first

### Objective
Create failing tests that describe the desired invariant: **rendered picker models and accepted picker selections must always match**.

### Files likely to change
- `tests/gateway/` new Telegram picker regression tests
- `tests/hermes_cli/` provider catalog tests
- `tests/gateway/test_telegram_model_picker_*.py` (new)

### Tests to add
1. **Codex picker/selection parity**
   - Given picker catalog includes `gpt-5.5`
   - When selecting `gpt-5.5`
   - Then switch succeeds
2. **Codex text validation uses live credentials**
   - Given live API returns `gpt-5.5`
   - Then `/model gpt-5.5 --provider openai-codex` is accepted
3. **Ollama Launch always includes documented recommended models**
   - Given config contains only two `ollama-launch` models
   - Then picker still includes four documented recommended cloud models plus user extras
4. **Ollama Launch config does not erase recommended models**
5. **Provider rows remain distinct**
   - `ollama-launch` and `ollama-cloud` do not accidentally collapse into one row

### Acceptance gate
Do not implement logic changes until these tests exist and fail for the expected reasons.

---

## Phase 2 — Extract catalog builder

### Objective
Refactor provider discovery into a reusable, surface-aware catalog resolver.

### Files likely to change
- Create: `hermes_cli/picker_catalog.py` (new)
- Modify: `hermes_cli/model_switch.py`
- Modify: `gateway/run.py`
- Modify: `gateway/platforms/telegram.py`

### Responsibilities of new module
- Build resolved provider entries for UI
- Handle provider-specific discovery rules
- Attach source/fingerprint metadata
- Return stable ordering
- Centralize dedup rules

### Non-goals
- Do not move every model-switch behavior here
- Focus only on picker-visible catalog resolution and selection validation inputs

---

## Phase 3 — Codex parity hardening

### Objective
Guarantee that live `openai-codex` picker data and validation cannot drift.

### Changes
- Update interactive picker selection path to validate against stored snapshot instead of recomputing provider catalog from scratch
- Update text `/model` validation path for `openai-codex` to pass runtime token to live catalog lookup
- Add explicit fallback policy object / helper
- Add debug trace message for source path used during validation

### Files likely to change
- `hermes_cli/models.py`
- `hermes_cli/model_switch.py`
- `gateway/run.py`
- Possibly `hermes_cli/codex_models.py`

### Acceptance criteria
- If picker shows `gpt-5.5`, click succeeds
- If live Codex catalog returns `gpt-5.5`, text switch succeeds
- If live fetch fails, fallback behavior is visible and tested

---

## Phase 4 — Ollama Launch architecture fix

### Objective
Restore documented `ollama launch hermes` behavior in picker without depending on accidental config state.

### Changes
- Define a dedicated merge helper for `ollama-launch`
- Seed from docs-backed recommended list already embedded in `_PROVIDER_MODELS["ollama-launch"]`
- Merge in config models from `providers.ollama-launch`
- Preserve current/default model prominence
- Prevent section ordering / dedup logic from erasing recommended cloud models

### Files likely to change
- `hermes_cli/model_switch.py`
- `hermes_cli/models.py`
- tests under `tests/hermes_cli/`
- tests under `tests/gateway/`

### Acceptance criteria
- Telegram picker for `ollama-launch` shows documented recommended cloud models
- Config extras remain visible
- No API key required for documented launch flow
- Native `ollama-cloud` remains separately discoverable when appropriate credentials exist

---

## Phase 5 — Observability and regression armor

### Objective
Make future catalog regressions diagnosable quickly.

### Changes
- Add debug metadata for provider discovery source (`live`, `cache`, `config`, `recommended-merge`, `windows-fallback`)
- Add regression tests spanning picker rendering + callback selection
- Add one high-level end-to-end gateway test for Telegram model picker flow

### Files likely to change
- `gateway/platforms/telegram.py`
- `gateway/run.py`
- `tests/gateway/...`

### Acceptance criteria
- Logs clearly show why a provider/model was shown
- A future mismatch breaks tests before release

---

## 5. Candidate files to change

Primary:
- `hermes_cli/model_switch.py`
- `hermes_cli/models.py`
- `hermes_cli/codex_models.py`
- `gateway/run.py`
- `gateway/platforms/telegram.py`

Tests:
- `tests/hermes_cli/test_codex_cli_model_picker.py`
- `tests/hermes_cli/test_ollama_cloud_provider.py`
- new `tests/hermes_cli/test_ollama_launch_picker.py`
- new `tests/gateway/test_telegram_model_picker_parity.py`

---

## 6. Verification plan

## Targeted tests
- `pytest tests/hermes_cli/test_codex_cli_model_picker.py -q`
- `pytest tests/hermes_cli/test_ollama_cloud_provider.py -q`
- `pytest tests/hermes_cli/test_ollama_launch_picker.py -q`
- `pytest tests/gateway/test_telegram_model_picker_parity.py -q`

## Integration slice
- Run gateway/model-related Telegram tests together
- Run any TUI/model picker tests that share provider discovery logic

## Final regression slice
- Run focused full suite for relevant areas before broader suite:
  - `tests/hermes_cli/`
  - `tests/gateway/`

---

## 7. Risks and tradeoffs

### Risk: overcoupling picker and validator
Mitigation: share snapshot contract only for interactive picker path; keep text-command validation independently live-capable.

### Risk: `ollama-launch` vs `ollama-cloud` semantics remain confusing
Mitigation: encode explicit provider policy rules and add tests proving separation.

### Risk: docs-backed recommended lists may change later
Mitigation: keep provider policy explicit and make recommended list source centralized; consider a later follow-up to externalize docs-backed recommendations into one dedicated provider-policy table.

---

## 8. Non-goals for this round
- Do not redesign all `/model` behavior across every platform
- Do not modify persistent config formats unless strictly necessary
- Do not add speculative provider policies beyond the currently failing surfaces

---

## 9. Recommended execution order
1. Write failing parity tests
2. Extract unified picker catalog layer
3. Fix Codex parity using snapshot-backed validation
4. Fix Ollama Launch recommended-model merging
5. Add observability and final regression tests

---

## 10. Approval request

This plan intentionally avoids a short-term patch. It changes the picker architecture so the same class of failures is much less likely to recur.

If approved, implementation should proceed in phases with a checkpoint after:
- Phase 1 tests
- Phase 3 Codex parity
- Phase 4 Ollama Launch fix
