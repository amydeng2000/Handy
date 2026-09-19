# Flow Context Demo Implementation Plan

> **For agentic workers:** Execute the tasks in order, with a review after each working increment. Keep this prototype on the local `flow-context-demo` branch until the demo is validated.

**Goal:** Make a short Handy dictation in a fresh third-party app expand into a useful, source-grounded prompt about an existing problem, then repeat the experience in a second app.

**Architecture:** A Python service in `flow-context/` implements Handy's custom post-processing API. It reads one active thread of curated moments, asks an LLM to synthesize the current state and select supporting moments, and returns the original utterance with a compact visible context packet. Handy performs transcription and paste with its existing shortcut.

**Tech stack:** Handy 0.9.7 (Tauri 2, Rust, React), Python 3.11+, FastAPI, httpx, python-dotenv, pytest.

**Spec:** [Flow Context demo design](../specs/2026-09-18-flow-context-demo-design.md)

## Global constraints

- Keep the MVP compatible with the unmodified Handy release. Do not build a transcription engine, meeting recorder, browser capture, agent chat UI, or vector database.
- Serve only on `127.0.0.1`; load all LLM credentials from an ignored `.env` through `python-dotenv`; never pass them on the command line or commit them.
- Keep real conversation and meeting data in ignored local JSON. Every moment has an `origin` value of `real` or `synthetic`; committed example data must be labeled synthetic and must not portray hypothetical meetings as real.
- Select one active `thread_id` from configuration. Ignore moments with other thread IDs; the MVP cannot infer what an unanchored “this” refers to across multiple threads.
- Preserve source role and stance. An AI suggestion, a rejected proposal, and the user's current decision are different facts.
- Return the raw utterance when synthesis fails; keep Handy auto-submit disabled for the demo.

## File map

| Path | Responsibility |
| --- | --- |
| `.gitignore` | Ignore `flow-context/.env` and `flow-context/data/*.local.json` |
| `flow-context/pyproject.toml` | Python runtime and test dependencies |
| `flow-context/.env.example` | Document non-secret config names and local dataset path |
| `flow-context/data/example_moments.json` | Clearly synthetic, conflicting `Future of Flow` moments |
| `flow-context/flow_context/__init__.py` | Python package marker |
| `flow-context/flow_context/config.py` | Load `.env` and validate service and LLM settings |
| `flow-context/flow_context/models.py` | Moment and context packet validation |
| `flow-context/flow_context/store.py` | Read and validate the active thread's JSON moments |
| `flow-context/flow_context/synthesis.py` | LLM request, response validation, and prompt composition |
| `flow-context/flow_context/server.py` | Handy-compatible model and chat endpoints, last-use debug metadata |
| `flow-context/tests/` | Data, synthesis, and API contract tests |
| `flow-context/README.md` | Setup, Handy settings, demo script, and recovery steps |

## Task 1: Create a truthful, private-by-default moment store

**Interface:** `load_moments(path: Path, thread_id: str) -> list[Moment]`. A `Moment` has `id`, `date`, `thread_id`, `source_type` (`voice`, `ai_chat`, `meeting`, `document`), `author_role` (`user`, `ai`, `other`), `stance` (`observation`, `proposal`, `rejection`, `decision`, `open_question`), `origin` (`real`, `synthetic`), and `text`. IDs are unique; moments are sorted by date. `config.py` defines `LlmConfig(base_url: str, model: str, api_key: str)` and an active thread title.

- [ ] Write `tests/test_store.py` with a valid two-moment fixture and assertions that malformed source types, duplicate IDs, missing attribution, and missing origin fail validation. Include a moment with a different `thread_id` and assert it is excluded.
- [ ] Run `python -m pytest tests/test_store.py -q`; expect the initial test to fail because the package does not exist.
- [ ] Add the package files, `pyproject.toml`, `.env.example`, and ignore rules. `config.py` calls `load_dotenv()`; it reads `FLOW_CONTEXT_MOMENTS_PATH`, `FLOW_CONTEXT_THREAD_ID`, `FLOW_CONTEXT_THREAD_TITLE`, `FLOW_CONTEXT_LLM_BASE_URL`, `FLOW_CONTEXT_LLM_MODEL`, and `FLOW_CONTEXT_LLM_API_KEY` from the environment after `.env` is loaded. The store rereads JSON on each dictation so new records appear without a service restart. The example file uses synthetic moments inspired by the shared thread: reflection idea, AI proposal, user's workplace objection, cross-app context direction, and unresolved intervention question.
- [ ] Run `python -m pytest tests/test_store.py -q`; expect PASS. Run `git check-ignore flow-context/.env flow-context/data/private.local.json`; expect both paths printed.
- [ ] Review every committed example moment for its `author_role` and `stance`, then commit this increment with a conventional `feat:` message.

Example assertion to drive the schema:

```python
moments = load_moments(example_path, "future-of-flow")
assert moments[0].thread_id == "future-of-flow"
assert all(m.origin == "synthetic" for m in moments)
assert any(m.author_role == "ai" and m.stance == "proposal" for m in moments)
assert any(m.author_role == "user" and m.stance == "rejection" for m in moments)
```

## Task 2: Synthesize current context without losing who believed what

**Interface:** `async synthesize(utterance: str, moments: list[Moment], client: httpx.AsyncClient, config: LlmConfig) -> ContextPacket | None`; `format_prompt(utterance: str, thread_title: str, packet: ContextPacket) -> str`. `ContextPacket` contains `current_direction`, `why_it_changed`, `open_questions`, and `source_ids`. The LLM must choose IDs from the supplied moments; the code rejects unknown IDs, empty direction, and packets above the configured length limit.

- [ ] Write `tests/test_synthesis.py` using `httpx.MockTransport` or a fake adapter. Assert that a returned packet references real IDs, excludes an unrelated moment, states that a rejected AI proposal was rejected, and places the exact utterance last. Assert that a packet using a synthetic moment says `Illustrative demo context` and marks that source. Add cases for malformed JSON, unknown IDs, timeout, and an empty response; each returns no packet so the caller uses the original utterance.
- [ ] Run `python -m pytest tests/test_synthesis.py -q`; expect FAIL before implementation.
- [ ] Implement one nonstreaming call to the configured OpenAI-compatible `/chat/completions` endpoint. Supply all moments in the active thread plus instructions to treat user decisions as more authoritative than earlier AI proposals. Request a compact JSON packet and validate it before composing text. Reject a context packet longer than 1,600 characters and use the raw utterance instead; never cut the user's request.
- [ ] Run the synthesis tests; expect PASS. Manually inspect one generated packet against the example dataset and confirm that its cited IDs support its claims.
- [ ] Commit this increment with a conventional `feat:` message.

Required prompt shape:

```text
Flow Context — Future of Flow
Current direction: ...
Why it changed: ...
Still open: ...
Sources: voice-01 (Sep 16), chat-02 (Sep 17), chat-04 (Sep 18)

My request: <the exact dictated utterance>
```

## Task 3: Expose the protocol Handy already uses

**Interface:** `GET /v1/models` returns an OpenAI-compatible model list containing `flow-context`. `POST /v1/chat/completions` accepts `model`, `messages`, `stream: false`, and extra Handy fields such as `reasoning_effort`; it returns `choices[0].message.content` with the expanded prompt. `GET /debug/last` returns only thread ID, selected source IDs, dates, types, author roles, origins, and output length. No source list appears in Handy's UI.

- [ ] Write `tests/test_server.py` using FastAPI's test client. Post a Handy-shaped request with `reasoning_effort: "none"` and verify the response shape and exact original utterance. Check `/v1/models`, empty input, model mismatch, and synthesis failure. Assert debug metadata contains no full moment text or API key.
- [ ] Run `python -m pytest tests/test_server.py -q`; expect FAIL before implementation.
- [ ] Implement request parsing and response serialization in `server.py`. Accept a raw `${output}` message and, for setup resilience, extract text from the default Handy `<transcript>...</transcript>` wrapper if present. Do not answer the user's question inside the service; return a prompt for the receiving app. Use a bounded request timeout and return the original utterance on model errors.
- [ ] Run `python -m pytest -q`; expect PASS. Start the service on loopback and send a local, credential-free fixture request to both endpoints; check that the returned JSON matches Handy's `choices[0].message.content` expectation.
- [ ] Commit this increment with a conventional `feat:` message.

Representative Handy request:

```json
{
  "model": "flow-context",
  "messages": [{"role": "user", "content": "Given everything I've thought about this, what am I still missing?"}],
  "stream": false,
  "reasoning_effort": "none"
}
```

## Task 4: Run the two-app demo and document it

- [ ] Write `flow-context/README.md` with Python setup, `.env` creation from `.env.example`, a JSON template for `data/moments.local.json`, and `python -m uvicorn flow_context.server:app --host 127.0.0.1 --port 8000`. Explain that one record represents one dated thought or one attributed turn, that the service rereads the file for each dictation, that `FLOW_CONTEXT_THREAD_ID` selects the active topic until the service restarts, and that all moments in the active thread are sent to OpenAI for synthesis. The app itself loads `.env` with `python-dotenv`; commands contain no credential values.
- [ ] Record the user's reported official Handy baseline: recording, transcription, and paste work locally. If any part fails during integration, reproduce it in a plain text field before debugging the Flow Context service.
- [ ] In Handy, enable post-processing, select **Custom**, set base URL `http://127.0.0.1:8000/v1`, select `flow-context`, and create/select a prompt containing only `${output}`. Keep auto-submit off. Verify the separate post-processing shortcut, which defaults to `Option+Shift+Space` on macOS unless reassigned.
- [ ] Rehearse a fresh ChatGPT conversation with the first underspecified utterance from the spec, inspect `/debug/last`, then repeat in a fresh second agent or coding surface. Check that the context packet reflects the same current direction and changes emphasis for the second request. Capture the exact words spoken, selected source IDs, and any failure in a local demo log that contains no private source text.
- [ ] Stop the local service and confirm Handy falls back to the raw transcript. Document that behavior and a restart step in the README.
- [ ] Run `python -m pytest -q`, `git status --short`, and a tracked-file scan for `.env` and `*.local.json`. Commit the runbook after the live demo passes.

## Optional later step: native Handy treatment

Only if the sidecar demo works and the visible prompt expansion needs a stronger visual cue, add a short “Context added from N moments” status to Handy's overlay. Inspect `src-tauri/src/actions.rs`, `src/overlay/RecordingOverlay.tsx`, and the existing overlay events before designing that change. This step requires a separate approved design, a local Tauri build, and macOS permission testing. It is not required for the MVP.

## Review checklist

- [ ] The third-party agent receives context from more than one source and answers the user's short request without a recap.
- [ ] Earlier AI suggestions rejected by the user are labeled as such.
- [ ] Only a dedicated Handy shortcut invokes Flow Context; ordinary dictation still works.
- [ ] No real private moments or credentials are tracked by git.
- [ ] The README describes the visible prompt-expansion limitation honestly.
