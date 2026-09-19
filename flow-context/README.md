# Flow Context demo for Handy

This local service lets the official Handy app paste an expanded prompt into a fresh ChatGPT chat, coding agent, or other text field. Handy transcribes your speech. The service reads one curated thread of earlier conversations, asks the configured OpenAI model for a short cited context packet, and returns that packet followed by your exact request. The receiving app answers the expanded prompt. The service does not answer the request itself.

The pasted text is visible in the destination app. Source IDs and `real`/`synthetic` labels appear there; `/debug/last` shows additional source metadata. No source panel is added to Handy's UI.

## 1. Prepare the service

Use Python 3.11 or newer. From this `flow-context/` directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
```

Edit `.env` locally. Put your OpenAI API key in `FLOW_CONTEXT_LLM_API_KEY`; do not put it in a terminal command or in Handy. The example dataset is safe to use for a dry run, but it is illustrative and every record is labeled `synthetic`. The service loads `.env` with `python-dotenv`. Both `.env` and local conversation files are ignored by git.

| Setting | Use |
| --- | --- |
| `FLOW_CONTEXT_MOMENTS_PATH` | JSON file for the one active thread; relative paths start in `flow-context/` |
| `FLOW_CONTEXT_THREAD_TITLE` | Title shown at the top of the pasted packet |
| `FLOW_CONTEXT_LLM_BASE_URL` | OpenAI-compatible API base URL, including `/v1` |
| `FLOW_CONTEXT_LLM_MODEL` | Upstream model used to synthesize context |
| `FLOW_CONTEXT_LLM_API_KEY` | Upstream API key, stored only in `.env` |

To use your own thread, save its converted records as `data/moments.local.json` and set `FLOW_CONTEXT_MOMENTS_PATH=data/moments.local.json`. The service rereads this file on every dictation; record edits do not require a restart. Changing `.env` requires a restart.

## 2. Supply your conversation thread

Fill one copy of the [conversation template](../docs/flow-context-conversation-template.md) and attach the `.md` or `.txt` file in chat. You can also keep a local copy under `data/` with a `.local.md` or `.local.txt` suffix. You do **not** need to write JSON or classify stances. We will convert the completed template to `data/moments.local.json` and set its `origin` to `synthetic` when the material is synthetic. Approximate dates and `Day 1` labels are fine; the conversion preserves order using demo dates.

A **moment** is an internal citeable unit: one attributed chat turn, one voice thought, or one whole meeting summary. It is not a summary of the thread. The full text of each unit goes into the local JSON index, along with its conversation and source description. All units in the active file are available to synthesis; the short packet pasted into another app cites only the ones it uses. Your Markdown remains the readable source file.

The internal JSON is a nonempty array of records. A single record looks like this:

```json
{
  "id": "chat-03",
  "conversation_id": "conversation-1",
  "source_label": "ChatGPT shared conversation (condensed paraphrase)",
  "date": "2026-09-17",
  "source_type": "ai_chat",
  "author_role": "user",
  "stance": "rejection",
  "origin": "synthetic",
  "text": "A standalone reflection app misses the moment when I continue work elsewhere."
}
```

`source_type` is `voice`, `ai_chat`, `meeting`, or `document`. `author_role` is `user`, `ai`, or `other`. `stance` is `observation`, `proposal`, `rejection`, `decision`, or `open_question`. `origin` is `real` or `synthetic`. IDs must be unique and dates must use `YYYY-MM-DD`. The example in [data/example_moments.json](data/example_moments.json) shows a complete synthetic thread.

`conversation_id` and `source_label` are optional metadata. They keep turns from one conversation together and preserve the Markdown file's source description. The source label is also shown in `/debug/last` for selected records. The supplied Markdown is the canonical source; the JSON is a local index for synthesis and citations. Regenerate the JSON after editing the Markdown, since the running service reads the JSON file. A whole meeting summary can be one record, while a chat uses one record per speaker turn.

For this demo, **all records in the active file are sent to the configured OpenAI API** for each context synthesis. The model selects a smaller set of IDs to cite in the returned packet. The service has no ChatGPT account access, automatic import, background capture, or topic classifier. Use one thread per active file; name the problem in the spoken request.

## 3. Start and check the service

```sh
python -m uvicorn flow_context.server:app --host 127.0.0.1 --port 8000
```

In another terminal, check model discovery and the last-used source metadata:

```sh
curl http://127.0.0.1:8000/v1/models
curl http://127.0.0.1:8000/debug/last
```

`/debug/last` shows the thread title, selected IDs, dates, source types, author roles, origin labels, output length, and a short `fallback_reason` when context was not added. It contains no full source text, dictated words, or API key. Before the first request its source list is empty. If synthesis fails, times out, returns malformed content, cites unknown IDs, or exceeds the 1,600-character context limit, the service returns the raw dictated request and clears the debug source list.

## 4. Point the official Handy app at the service

The official Handy app is already working locally for recording, transcription, and paste. In Handy settings:

1. Open **Advanced** in Handy's sidebar. Under **App**, turn on **Experimental Features**. Scroll to **Experimental** and turn on **Post Processing**. A **Post Process** item then appears in the sidebar.
2. Open **Post Process** and choose the **Custom** provider.
3. Set **Base URL** to `http://127.0.0.1:8000/v1`. Leave Handy's **API Key** blank. Select or create model `flow-context`. Refresh the model list after entering the URL if needed.
4. Create and select a post-processing prompt whose entire **Prompt Instructions** field is `${output}`. This sends the transcription to the local service without additional instructions.
5. In **Advanced** → **Output**, set **Auto Submit** to **Off** so you can inspect the pasted context before sending it.
6. On **Post Process**, check the separate **Transcribe with Post Processing** shortcut. Its macOS default is `Option+Shift+Space`; use the binding shown in your app if you changed it. Ordinary transcription has its own shortcut.

You do not need to build the Handy fork for this stage. If Handy cannot record or paste during integration, first try its ordinary shortcut in a plain text field to isolate the baseline issue.

## 5. Rehearse the two-app moment

1. Open a fresh ChatGPT conversation. Focus the prompt field. Invoke Handy's post-processing shortcut and say a short request that names your thread, such as “Given everything I've thought about Flow Context, what am I still missing?”
2. Inspect the pasted prompt before submitting. It should show **Current direction**, **Why it changed**, **Still open**, source markers, and your exact words under **My request**. The example dataset adds **Illustrative demo context**; real and synthetic source markers stay distinct.
3. Open `http://127.0.0.1:8000/debug/last` locally and verify that the selected IDs support the summary. An earlier AI proposal should be described as rejected if a later user turn rejected it.
4. Open a fresh second agent or coding surface. Say “Can you turn the direction I've landed on for Flow Context into the smallest implementation plan?” The same thread should appear with emphasis suited to this request.
5. Record the exact spoken requests, selected source IDs, and any failure in an ignored local file such as `data/demo-log.local.md`. Do not copy private source text or credentials into a log or issue.

A mocked API test verifies the expanded response shape; a local credential-free HTTP check verifies raw-text fallback. A live rehearsal also requires an active conversation file, an `.env` key, and authorization to send all records in that file to the configured OpenAI API.

## Recovery

- If the service returns only your spoken words, inspect `fallback_reason` at `/debug/last`, then check that `.env` has a key and the moments path exists. Restart the service after `.env` or code changes. The server intentionally falls back to raw dictation on synthesis errors.
- If Handy cannot reach the service, check the Base URL and that the loopback server is still running. Stop the service with `Ctrl+C` and restart with the command above. When the service is stopped, Handy's post-processing error path falls back to its original transcription; the ordinary transcription shortcut also remains available.
- If the wrong model appears, refresh the custom provider model list or create `flow-context` manually in Handy's model selector.

Run the automated checks with `python -m pytest -q` from this directory.
