# BV chat behavior — verification checkpoint

**Date:** 2026-11-16  
**Branch:** `master`  
**Scope:** Forked `llama-server` chat role used by the Windows test edition; not the original Bright Vale repository.  
**Disposition:** **SOURCE WIRED / STATIC CHECK PASS; WINDOWS AND LINUX RUNTIME NOT VERIFIED.**

## Behavior objective

Enforce `professional-v1` **only** for opt-in `BV_INFERENCE_ROLE=chat`. It instructs the model to:

- Use a neutral, strictly professional tone; no unsolicited humor, sarcasm, emojis, flattery, or nicknames.
- Identify the exact subject, model, edition and units before asserting facts; never substitute a similar entity.
- Avoid unsupported numerical details, fabricated memories, sources, or claims of having verified anything.
- Reassess disputed claims objectively; neither reflexively reject nor automatically agree with user corrections.
- Distinguish general statements from individual exceptions and say when evidence is insufficient.

**No topic-specific factual patches** are present in the profile. The fork does not acquire external verification tools or authority over data. Perl remains responsible for evidence and final reply acceptance.

## Tracked source change

| Commit | Scope |
| --- | --- |
| `a55f9fbf0f` | Added `tools/server/bv-chat-behavior.h`, the fixed, topic-neutral professional prompt. |
| `4d48182fdd` | Injected the system instruction into `/v1/chat/completions` only when the inference role is `chat`; profile tag on accepted path. |
| `944d5cce6e` | Added a smoke-test assertion for the profile header and redacted error diagnostics for the previously rejected valid chat request. |

## Verification evidence

- **Static source contract: PASS (18 of 18 inspected assertions)** on commit `944d5cce6e`. Confirmed profile name, exact-subject rules, neutral style, uncertainty, correction handling, exception/general-case distinction, chat-only activation, 1 MiB post-injection guard, preexisting role gate, profile-response marker, positive chat smoke assertion, and Windows/Linux CI matrix. Also inspected the included Qwen3 template: it supports multiple system-role messages. This is a source inspection, **not a C++ compilation or model behavior result**.
- **Windows and Linux source build on the current behavior commit: NOT RUN / NO CI EVIDENCE.** The GitHub Actions run listing and commit check-runs query returned **zero runs/checks** for `944d5cce6e`. Do not infer a build pass from successful commits. The existing `.github/workflows/bv-inference-build.yml` has a `workflow_dispatch` route for a manual Actions run if automatic runs are not being triggered by API-created commits.
- **Existing failure on previous fork revision: OPEN / FAIL.** [Run `43734669788`](https://github.com/bosnatron/llama.cpp/actions/runs/43734669788) at `9c6f4ad4d1` compiled the server but returned HTTP **403** for an apparently valid bounded chat request on **both Windows and Linux** (expected 200). Existing negative security checks passed. Exact cause remains unverified; the new smoke diagnostics preserve only a synthetic response excerpt and a bounded log tail.
- **Actual Qwen3 model behavior: NOT TESTED.** The fork smoke test uses a SHA-pinned tiny synthetic GGUF, which cannot validate truthfulness, correction handling, response quality, or tone with the production Qwen GGUF.

## 2026-11-17 — Correct pre-routing POST-body timing (HTTP 403)

- **Historical failure reproduced from archived CI logs, not rerun today:** [run 43734669788](https://github.com/bosnatron/llama.cpp/actions/runs/43734669788) compiled on both Windows and Linux and passed the restricted endpoint/host/browser/tool/cache denial checks, but its first allowed chat POST failed with HTTP 403.
- **Root cause identified in source:** `bv_is_allowed_request()` parsed `req.body` inside cpp-httplib's `set_pre_routing_handler`. cpp-httplib invokes pre-routing **before reading the request body**, so a legitimate JSON POST cannot pass the body-content checks there. This applies to both chat and embedding roles.
- **Narrow source correction:** [commit b1f2495](https://github.com/bosnatron/llama.cpp/commit/b1f24951e0f346427373b17721c133f862b36359) changes only `tools/server/server-http.cpp`: early pre-routing still enforces loopback-only peers/Host, no browser Origin/fetch headers, allowed method/endpoint and JSON content-type. POST JSON parsing, role/message/tool/function/cache/stream restrictions and 1 MiB body-size check execute in the matched POST handler **after** cpp-httplib reads the body, before it reaches inference. The chat-only professional system instruction and profile header still apply after authorization. No request content is logged.
- **Verification status:** reviewed corrected source call sites and preserved deny conditions; **Windows/Linux compile, positive HTTP 200, negative HTTP 403, embedding and real-Qwen runtime tests are NOT YET VERIFIED on this commit**. Do not mark the earlier 403 resolved by CI evidence until a new workflow runs and passes.
- **Next:** run `.github/workflows/bv-inference-build.yml` on `master` at `b1f2495`, check Windows and Linux valid-chat/embedding and negative/security assertions, preserve any failures, then calibrate with pinned Qwen and verify Windows Perl integration. Do not relax security gates or claim installer acceptance.
- **Original Bright_Vale repository untouched.**

### 2026-11-17 — POST-body negative regression coverage

- **Added six smoke-test cases** to `tools/server/tests/bv_inference_smoke.py` in [commit `b36001d`](https://github.com/bosnatron/llama.cpp/commit/b36001dcbf3f95a8f9b50ed6c8248a6a35a16e32): chat role rejects JSON array, empty messages and object-valued message content; embedding role rejects JSON array, missing input and object-valued input. These supplement existing tool/browser/cache/stream denial tests and successful authorized chat/embedding cases. The workflow already includes this file in its push path filters.
- **Evidence state:** source change committed and test cases inspected; **no Windows/Linux execution result verified yet** for this test revision. A GitHub commit/status query returned no reported statuses, which alone does not establish that Actions ran or failed. Do not mark the repaired positive-chat HTTP 403 or negative tests PASS without job logs.
- **Next:** collect the Windows/Linux `bv-inference-build.yml` run for commit `b36001d` (or dispatch the workflow manually if no run appears); inspect authorized HTTP 200 and denied HTTP 403 outcomes and profile attestation. Preserve failures and only then revise acceptance.

### 2026-11-17 — Actions history check: no corrected-code CI run

- **Read-only Actions verification:** GitHub Actions repository run listing (168 runs reported, first 30 most recent inspected) shows no run newer than 2026-11-15 and no workflow execution for corrected commits [`b1f2495`](https://github.com/bosnatron/llama.cpp/commit/b1f24951e0f346427373b17721c133f862b36359) or [`b36001d`](https://github.com/bosnatron/llama.cpp/commit/b36001dcbf3f95a8f9b50ed6c8248a6a35a16e32). Latest observed `BV inference-only fork build` is historical [run 43734669788](https://github.com/bosnatron/llama.cpp/actions/runs/43734669788) at `9c6f4ad`, failed on Windows and Linux (legitimate chat 403). A GitHub commit status list alone is not proof of a workflow run.
- **Acceptance:** corrected-source Windows build, Linux build, positive chat HTTP 200, embedding HTTP 200, all negative HTTP 403, and professional-v1 attestation remain **NOT TESTED / NOT VERIFIED**. No deployment or workaround was performed.
- **Blocker and next action:** no workflow-dispatch capability is exposed by the present GitHub connection; manually select **Actions → BV inference-only fork build → Run workflow → master** in the fork, then inspect both jobs and preserve log evidence before updating this record. Do not relax authorization or mark PASS without a linked run. The original `Bright_Vale` is untouched.

## 2026-11-17 — Source contract re-inspection after HTTP 403 repair

- **Inspection only, no server execution or source change.** Read the latest `tools/server/server-http.cpp`, `tools/server/tests/bv_inference_smoke.py`, and `.github/workflows/bv-inference-build.yml` from `master`; confirmed corrected request-stage handling and smoke coverage.
- **15/15 bounded source-contract assertions PASS:** early routing without JSON parsing; pre-routing gate explicitly early-only; post-handler JSON authorization; authorization before inference; strict loopback/Host checks; browser request denial; 1 MiB body bound; JSON/cache restriction; forbidden tools/functions/MCP; limited message roles; no streaming; professional instruction insertion only after authorization; opt-in behavior preserving unmodified upstream mode; negative chat/embedding body tests; positive chat/embedding test cases retained. This was an inspection of source text and control flow, **not a compiler test, HTTP execution, security penetration test, or model-quality acceptance**.
- **CI history remains unchanged at last check:** no verified corrected-code Windows/Linux Actions jobs. Historical [failed run 43734669788](https://github.com/bosnatron/llama.cpp/actions/runs/43734669788) remains retained. No API-triggered workflow dispatch was available through the connected action interface.
- **Next acceptance gate:** run the existing `BV inference-only fork build` on `master`; review both OS job logs, accepted chat/embedding HTTP 200 and hostile HTTP 403 outcomes, and professional-v1 response attestation. Keep any unresolved behavior explicit and record exact run SHA before claiming PASS.

### 2026-11-17 — Workflow trigger eligibility and absent-run inspection

- **Read-only trigger investigation:** inspected `.github/workflows/bv-inference-build.yml` on fork `master` (blob `ae7a997dc5832b1f9bf280725c62ad2a25056cef`). It declares `push` to `master`, restricted to `tools/server/server-http.cpp`, `tools/server/tests/bv_inference_smoke.py`, and its own workflow file; `workflow_dispatch` is also declared. Thus both the C++ correction `b1f2495` and regression-test change `b36001d` match the path filters on their face.
- **Observed GitHub Actions history:** repository run-list response reports 168 existing runs, newest created 2026-11-15 20:53:39 UTC; newest `BV inference-only fork build` remains [43734669788](https://github.com/bosnatron/llama.cpp/actions/runs/43734669788) at pre-fix `9c6f4ad`, **FAIL** on the legitimate chat request for both OSes. No corrected-code workflow execution was discovered. This is evidence of a missing trigger/run, **not proof of why** the event was suppressed. Workflow enablement and trigger credentials cannot be established through available connector actions.
- **Disposition:** source-eligibility inspection **PASS**, actual Windows/Linux CI **NOT RUN / NOT VERIFIED**. Do not create extraneous source changes to force a build, retry the historical pre-fix SHA as though it tested the repair, or weaken any role restrictions.
- **Next:** use GitHub Actions **Run workflow** on `master` via a workflow-dispatch-capable interface; inspect both matrix jobs and their precise head SHA; record accepted chat/embedding HTTP 200 and forbidden requests HTTP 403, or any remaining failure with logs.

### 2026-11-17 — Windows launcher now requires both real inference roles

- [x] **Cross-repository integration source update:** [`BV_Microsoft_Test` commit `cff2c95`](https://github.com/bosnatron/BV_Microsoft_Test/commit/cff2c9545e312bdca04d91723d12371e48362750) adds synthetic `/v1/embeddings` and `/v1/chat/completions` checks after launcher health/role checks and before enabling the Windows assistant interface. Chat request sets `cache_prompt:false`, `stream:false`, bounded tokens and no tools; both model responses must attest the expected inference role, and Qwen must attest `professional-v1`. Errors refuse startup.
- [ ] **Execution pending:** no Windows launcher parsing, actual model inference, or negative cleanup verification has been executed on this new change. It does not establish resolution of the earlier forked server HTTP 403 or final packaging acceptance.
- **Next:** verify `llama.cpp` corrected Windows/Linux server first, then test these two startup probes with pinned Qwen/Nomic files in an integrated Windows candidate. This is a companion integration note; no fork inference source modified.

## QA/QC required before acceptance

1. Obtain a fresh Actions run on the new revision and confirm **both** Windows and Linux compilation, valid-chat HTTP 200, profile attestation, and security refusal checks. If HTTP 403 recurs, inspect the diagnostic response and fix its cause **without relaxing loopback, non-tool, no-browser, no-cache or role restrictions**.
2. Test the actual pinned Windows Qwen GGUF with independent, topic-neutral scenarios spanning entity mix-ups, uncertain factual quantities, false versus valid corrections, and general rules versus exceptions. Separate **prompt adherence** from **factual correctness**, log counterexamples, and reserve unseen holdout scenarios.
3. Run the final Perl fact/evidence gate, actual Windows launcher, local inference role separation and privacy regression tests. A passing synthetic smoke test alone is not product acceptance.

**Current result:** static integration **PASS**; forked server runtime **NOT VERIFIED**; earlier valid-chat **FAIL** open; Qwen calibration effectiveness **NOT TESTED**. No Windows installer, native DLL release or application acceptance is claimed.
