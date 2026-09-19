# Flow Context demo design

## Purpose

Demonstrate the return-to-problem moment described in the [shared brainstorming conversation](https://chatgpt.com/share/6aadb319-ee2c-83e8-af12-bc3759765f21): the user dictates an underspecified request into a fresh third-party agent, and Handy supplies the current state of a problem from earlier thoughts, AI exchanges, and other sources. The receiving agent can respond without a manual recap. The demo should work again after switching to another agent.

## Demo contract

1. Start a fresh ChatGPT conversation. With Handy's post-processing shortcut, dictate: “Given everything I've thought about this, what am I still missing?”
2. Handy pastes a short prompt containing the original request plus the relevant state of the `Future of Flow` thread. The pasted context is visible because Handy controls text insertion, not ChatGPT's hidden system context.
3. The expanded text pasted into the destination app ends with short source markers such as `voice-01 (Sep 16)` and `chat-02 (Sep 17)`. A local `GET /debug/last` view resolves those markers to date, source type, author role, and `real` or `synthetic` origin. It does not expose full source text. No source list appears in Handy's own UI in the MVP.
4. Switch to a fresh second agent or coding surface. Dictate: “Can you turn the direction I've landed on into the smallest implementation plan?” The same thread follows the user and the context packet reflects the new task.
5. Ordinary Handy dictation remains available through its separate transcription shortcut.

The user should be able to speak naturally in either surface. The receiving app should identify the direction, reasons for rejected ideas, and open questions without the user naming them in the new dictation.

## Recommended architecture

Use the checked-out Handy repository as the demo workspace, but start with a local sidecar service and Handy's existing **Custom** post-processing provider. Handy already sends a nonstreaming OpenAI-compatible request to `{base_url}/chat/completions` and pastes the returned `choices[0].message.content` into the focused app. Its custom provider has an editable base URL, and macOS has a separate post-processing shortcut. This proves the cross-app interaction without rebuilding the desktop app.

```text
spoken request -> Handy transcription -> custom post-processing request
                                    -> local Flow Context service
                                    -> curated thread moments + context synthesis
                                    -> compact enriched prompt
                                    -> Handy paste into the focused third-party app
```

Configure Handy's custom base URL as `http://127.0.0.1:8000/v1`, model as `flow-context`, and selected post-processing prompt as `${output}`. The service implements `GET /v1/models` and `POST /v1/chat/completions`; it accepts Handy's optional `reasoning_effort` field. No API key is needed in Handy. The service loads its upstream model credential from an ignored `.env` file using `python-dotenv`.

Handy sends the current transcription and selected prompt to its provider; it does not attach the local moment file. Sending that request directly to OpenAI would give the model no historical thread data. The local service reads the supplied thread file, asks OpenAI to synthesize the current state, and returns an enriched prompt in the response format Handy already expects.

The first release treats the supplied synthetic conversations as one problem thread. The user's demo dictation names that problem; the service does not classify topics or choose among threads. Context selection considers all 8–12 curated moments in the file, with no vector database, scraping, background capture, or automatic thread discovery. Each moment carries date, source, author role, stance, origin (`real` or `synthetic`), and text so an AI proposal later rejected by the user cannot be reported as the user's current belief. The synthesizer produces a bounded packet with current direction, why it changed, open questions, and source IDs. The original dictated request remains verbatim at the end.

If context generation fails or returns no trustworthy result, the service returns the original request. Do not invent context or silently substitute an unrelated thread. The service listens only on loopback. Handy's auto-submit setting stays off so the user can inspect the expanded prompt before sending it.

## Data and privacy

Commit only a clearly labeled synthetic example dataset. The user can supply the complete synthetic thread as one Markdown or text file using the [conversation template](../../flow-context-conversation-template.md): approximate date, source, and ordered speaker-labeled turns for each conversation. They do not need to write JSON or label stances. During setup, convert that file into `flow-context/data/moments.local.json`, keeping each attributed turn separate and marking it synthetic. The service rereads the JSON file for each dictation, so added moments are available on the next request. There is no upload UI or automatic ChatGPT account access in the MVP. The service should log source IDs, source types, origin labels, and character counts for the demo; it should not log full source text or API credentials. All moments in the file are sent to the configured OpenAI API for synthesis; the source markers identify the subset used in the returned context packet. Label the live prompt as illustrative and mark its source IDs as synthetic.

## Alternative approaches

| Approach | Value | Cost | Decision |
| --- | --- | --- | --- |
| Existing Handy app + local provider | Fastest path to the cross-app moment; no desktop build | Context appears in pasted prompt; no native memory badge | **MVP** |
| Handy directly to OpenAI with a fixed context prompt | No local service | Context must be copied into Handy settings and cannot update or select moments from the local store | Smaller static mock only |
| Modify Handy's Rust pipeline and overlay | Native “context added” treatment and richer status | Desktop build, permissions, event wiring, fork maintenance | Only after MVP works |
| Browser extension or agent integration | Could pass context in a more native way | Different integration per destination; obscures the core demo | Outside demo scope |

## Success checks

- The first spoken request produces an accurate answer in a new ChatGPT chat using at least one voice thought and one AI conversation moment.
- A later rejection or decision overrides an earlier AI proposal in the expanded context.
- The second agent receives the same current problem state with phrasing suited to its request.
- With the local service stopped, Handy inserts the raw transcript rather than blocking dictation.
- The demo can be run from documented commands and settings, with no credentials or real private artifacts in git.

## Setup decision

Install and launch the official Handy macOS app first to confirm microphone permission, Accessibility permission, model download, shortcut behavior, and paste into a plain text field. Use that app for the sidecar MVP. Quit the official app before running a locally built Handy fork: the two builds share Handy's single-instance behavior and app identity. A local build is only needed for the optional native overlay stage.

This checkout is on `flow-context-demo`, with `upstream` pointing to `cjpais/Handy` and `origin` pointing to the user's GitHub fork. The user reported that the official Handy app is working locally.
