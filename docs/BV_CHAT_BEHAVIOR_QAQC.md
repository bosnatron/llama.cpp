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

## QA/QC required before acceptance

1. Obtain a fresh Actions run on the new revision and confirm **both** Windows and Linux compilation, valid-chat HTTP 200, profile attestation, and security refusal checks. If HTTP 403 recurs, inspect the diagnostic response and fix its cause **without relaxing loopback, non-tool, no-browser, no-cache or role restrictions**.
2. Test the actual pinned Windows Qwen GGUF with independent, topic-neutral scenarios spanning entity mix-ups, uncertain factual quantities, false versus valid corrections, and general rules versus exceptions. Separate **prompt adherence** from **factual correctness**, log counterexamples, and reserve unseen holdout scenarios.
3. Run the final Perl fact/evidence gate, actual Windows launcher, local inference role separation and privacy regression tests. A passing synthetic smoke test alone is not product acceptance.

**Current result:** static integration **PASS**; forked server runtime **NOT VERIFIED**; earlier valid-chat **FAIL** open; Qwen calibration effectiveness **NOT TESTED**. No Windows installer, native DLL release or application acceptance is claimed.
