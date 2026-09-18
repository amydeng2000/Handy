# Flow Context demo design

## Purpose

Demonstrate the return-to-problem moment described in the [shared brainstorming conversation](https://chatgpt.com/share/6aadb319-ee2c-83e8-af12-bc3759765f21): the user dictates an underspecified request into a fresh third-party agent, and Handy supplies the current state of a problem from earlier thoughts, AI exchanges, and other sources. The receiving agent can respond without a manual recap. The demo should work again after switching to another agent.

## Demo contract

1. Start a fresh ChatGPT conversation. With Handy's post-processing shortcut, dictate: “Given everything I've thought about this, what am I still missing?”
2. Handy pastes a short prompt containing the original request plus the relevant state of the `Future of Flow` thread. The pasted context is visible because Handy controls text insertion, not ChatGPT's hidden system context.
3. Show which source moments were used in a local debug view or console, including voice, user and AI chat turns, and any meeting excerpt. The demo must distinguish real artifacts from synthetic examples.
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

The first release has one explicitly active problem thread. Context selection considers all 8–12 curated moments in that thread, with no vector database, scraping, background capture, or automatic thread discovery. Each moment carries date, source, author role, stance, and text so an AI proposal later rejected by the user cannot be reported as the user's current belief. The synthesizer produces a bounded packet with current direction, why it changed, open questions, and source IDs. The original dictated request remains verbatim at the end.

If context generation fails or returns no trustworthy result, the service returns the original request. Do not invent context or silently substitute an unrelated thread. The service listens only on loopback. Handy's auto-submit setting stays off so the user can inspect the expanded prompt before sending it.

## Data and privacy

Commit only a clearly labeled synthetic example dataset. The shared ChatGPT conversation can inform that example, but its hypothetical meeting descriptions must not be presented as meetings that occurred. Real conversation excerpts, meeting notes, and `.env` stay in ignored local files. The service should log source IDs, source types, and token or character counts for the demo; it should not log full source text or API credentials.

## Alternative approaches

| Approach | Value | Cost | Decision |
| --- | --- | --- | --- |
| Existing Handy app + local provider | Fastest path to the cross-app moment; no desktop build | Context appears in pasted prompt; no native memory badge | **MVP** |
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

This checkout is a local clone on `flow-context-demo` with `upstream` pointing to `cjpais/Handy`. A GitHub-hosted fork cannot be created until GitHub authentication is restored in this environment.
