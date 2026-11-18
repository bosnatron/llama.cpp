# BOSNATRON / Bright Vale — no tracking and offline inference policy

**Scope:** `bosnatron/llama.cpp`, the fork from which Bright Vale's inference server is built.  
**Status:** Source policy implemented 2026-11-18; **not yet accepted on a rebuilt Windows binary**.

## Mandatory product promise

Bright Vale will not track people, installations, devices, or use of the product; will not send conversations, prompts, embeddings, databases, identity data, crash reports, or diagnostics to BOSNATRON or external analytics services; and will not silently fetch models, check updates, or call home. Customer information remains local and under the customer's control. There is no consent-based telemetry in this product: it is simply prohibited.

The **only network communication allowed by the Bright Vale inference processes** is the application's intended request/response traffic over loopback (`127.0.0.1` / `::1`). The Python smoke-test client also uses local loopback. Local HTTP requests are necessary for the bundled Perl app to communicate with Qwen and Nomic; **they are not a tracking website**. Privacy includes preventing unintended outbound traffic, not disabling local inference.

## Source audit and hardened controls

The reviewed upstream-derived fork contains generic optional remote features: Hugging Face/Docker model downloading (`common/download.cpp`, `common/hf-cache.cpp`), a `llama-connect` tunnel, UI/MCP proxy functionality, and a local `/metrics` endpoint. **Their presence is not evidence of spyware or existing telemetry**, but they are unsuitable for Bright Vale's private inference mode. Existing BV inference HTTP code already restricted remote listening, browser requests, MCP, tools, caches, unsafe endpoints and access to `/metrics`.

Additional hardening committed:

1. **`common/bv-inference-network-policy.h`:** any nonempty `BV_INFERENCE_ROLE` value (including invalid values pending rejection) forbids outbound HTTP client construction.
2. **`common/http.h`:** checks the BV policy **before URL parsing, DNS, proxy setup or HTTP client construction**. This covers the shared download/Hugging Face HTTP client factory; it does not interfere with the local `httplib::Server` that receives inference requests. Other generic upstream roles are outside this BV-only guarantee.
3. **`tools/server/server.cpp`:** rejects missing `--offline`, missing local model path and any Hugging Face/Docker remote model reference **before** attempting to resolve remote model metadata or start the router.
4. **`tools/server/server-http.cpp`:** rejects inherited Google Cloud `AIP_MODE=PREDICTION` routing in BV inference role, preventing cloud environment variables from replacing the loopback/port configuration.
5. **`tools/server/tests/bv_inference_smoke.py`:** **removed automatic HTTPS download of its model fixture**. A previously inspected local `BV_TEST_MODEL_PATH` is mandatory, and the pinned SHA-256 must match before the test will run. All actual inference HTTP smoke requests remain loopback-only.

The upstream generic features have **not been removed globally from every non-BV invocation** of llama.cpp. Do not claim that an arbitrary build or a standalone invocation with `BV_INFERENCE_ROLE` absent is an approved Bright Vale product. The final launcher must always establish the role, `--offline`, and a local GGUF path.

## Executed evidence / scope limitations

- **Executable C++ policy unit:** `tools/server/tests/bv_no_egress_policy_test.cpp`, compiled with GCC/G++ 14.2.0 and `-std=c++17 -Wall -Wextra -Werror` on local Linux, **8/8 role cases PASS**. No sockets or network requests were opened in this unit test.
- **Current connected GitHub source audit:** **16/16 static checks PASS**, covering the HTTP guard position, early model preflight, cloud-mode restriction, local network allowlist, absence of automatic smoke-test download and pinned local fixture. These checks inspected the exact current repository contents, not a rebuilt product binary.
- **Python regression committed but execution pending:** `tools/server/tests/test_bv_no_tracking.py` checks the source controls and patches `urllib.request.urlopen` so missing or unavailable smoke-test models cannot trigger network access. It has not been run against a complete byte-exact checkout in this environment.
- **No rebuilt Windows `llama-server.exe` was available for native verification.** Actual network/packet capture, process-level OS outbound restrictions, transitive dependency inventory, native DLL closure and signed bundle acceptance remain **OPEN**. These controls do not prove there are no remote connections in every other component of a future final product.

Reproduction in a **complete checkout** of this fork, with no model download required:

```sh
g++ -std=c++17 -Wall -Wextra -Werror -Icommon \
    tools/server/tests/bv_no_egress_policy_test.cpp -o /tmp/bv-no-egress-policy-test
/tmp/bv-no-egress-policy-test
python3 -m unittest discover -s tools/server/tests -p 'test_bv_no_tracking.py'
```

To perform the model inference smoke test, provide the already-pinned **local** `BV_TEST_MODEL_PATH` test file; never download model files automatically while testing. Windows release QA must build the exact audited source revision, verify the binary SHA-256 and run packet/network egress observation under synthetic chat and embedding workloads with outbound network denied. Any unplanned packet means **FAIL** and no release.

## Protected project boundaries

No changes to `bosnatron/Bright_Vale` (the protected original project). No customer conversation data, personal databases, private logs, installation records, model weights, telemetry keys or account identifiers have been uploaded. This privacy policy is binding for the complete BOSNATRON Windows edition even though this document audits only the llama.cpp fork.
