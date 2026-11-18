#!/usr/bin/env python3
"""Smoke-test the fork's opt-in Bright Vale inference-only HTTP roles.

Only public synthetic prompts and an ~1.2 MB test GGUF are used.
This tests runtime authorization, not Qwen/Nomic answer quality.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

# The smoke fixture is supplied locally; test execution must not download a
# model, send host information, or depend on an external model registry.
MODEL_SHA256 = "047bf46455a544931cff6fef14d7910154c56afbc23ab1c5e56a72e69912c04b"


def test_model(_directory):
    selected = os.environ.get("BV_TEST_MODEL_PATH")
    if not selected:
        raise RuntimeError(
            "Set BV_TEST_MODEL_PATH to a pre-reviewed local test GGUF; "
            "automatic network model downloads are forbidden."
        )
    path = Path(selected).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError("Pinned local test GGUF not found")
    with path.open("rb") as model:
        digest = hashlib.file_digest(model, "sha256").hexdigest()
    if digest != MODEL_SHA256:
        raise RuntimeError("Test GGUF checksum mismatch; refusing to run.")
    return path



def expanded_context_smoke_fixture(model, directory):
    """Derive a disposable large-context *transport test* from the pinned GGUF.

    The tiny upstream test model declares 128 trained tokens, whereas the
    mandatory professional-v1 system instruction requires ~886 tokens. This
    fixture changes only a known GGUF metadata integer, never model weights.
    It is NOT evidence of long-context model accuracy, training, or quality.
    The original download must already have passed its pinned SHA-256 check.
    """
    data = model.read_bytes()
    name = b"llama.context_length"
    matches = []
    for kind, fmt in ((4, "<I"), (10, "<Q")):
        old = struct.pack("<Q", len(name)) + name + struct.pack("<I", kind) + struct.pack(fmt, 128)
        if data.count(old) == 1:
            matches.append((old, struct.pack("<Q", len(name)) + name +
                            struct.pack("<I", kind) + struct.pack(fmt, 2048)))
    if len(matches) != 1:
        raise RuntimeError("Pinned tiny GGUF context metadata is not the expected 128 tokens")
    before, after = matches[0]
    generated = data.replace(before, after, 1)
    derived = Path(directory) / "stories260K-smoke-context2048.gguf"
    derived.write_bytes(generated)
    print("Synthetic transport fixture: changed GGUF context metadata only; "
          "output quality not tested.", flush=True)
    return derived


def available_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def http(port, path, method="GET", body=None, headers=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={
            **({"Content-Type": "application/json"} if data is not None else {}),
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def require_status(actual, wanted, label):
    if actual != wanted:
        raise AssertionError(f"{label}: expected HTTP {wanted}, received {actual}")
    print(f"PASS: {label} ({actual})", flush=True)


def wait_ready(process, port, logfile):
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Inference server exited ({process.returncode}) before ready: "
                + logfile.read_text(errors="replace")[-4000:]
            )
        try:
            status, _, _ = http(port, "/health")
            if status == 200:
                return
        except (OSError, TimeoutError):
            pass
        time.sleep(0.25)
    raise RuntimeError("Inference test server did not become healthy")


def exercise(binary, model, role, directory):
    port = available_port()
    logfile = Path(directory) / f"{role}.log"
    flags = [
        str(binary), "--model", str(model),
        "--host", "127.0.0.1", "--port", str(port),
        "--no-ui", "--offline", "--cors-origins", "localhost",
        "--no-slots", "--no-cache-prompt", "--no-cache-idle-slots",
        "--cache-ram", "0", "--slot-prompt-similarity", "0",
        "--parallel", "1", "--ctx-size", "2048", "--batch-size", "32",
    ]
    if role == "embedding":
        flags.extend(["--embedding", "--pooling", "mean"])
    environment = {**os.environ, "BV_INFERENCE_ROLE": role}
    with logfile.open("wb") as out:
        process = subprocess.Popen(
            flags, stdout=out, stderr=subprocess.STDOUT, env=environment
        )
        try:
            wait_ready(process, port, logfile)
            status, _, headers = http(port, "/health")
            require_status(status, 200, f"{role} health")
            if headers.get("Cache-Control", "").lower() != "no-store":
                raise AssertionError("BV inference response must set Cache-Control: no-store")
            if next((value for key, value in headers.items() if key.lower() == "x-bv-inference-role"), "").lower() != role:
                raise AssertionError("Server did not attest its expected inference role")
            for path in ("/", "/tools", "/slots", "/metrics",
                         "/v1/responses", "/v1/chat/completions/control",
                         "/lora-adapters", "/v1/messages"):
                require_status(http(port, path)[0], 403, f"{role} denies GET {path}")
            require_status(
                http(port, "/health", headers={"Host": "redirected.evil.example"})[0],
                403, f"{role} rejects DNS-rebound Host"
            )
            require_status(
                http(port, "/health", headers={"Origin": "http://localhost:3000"})[0],
                403, f"{role} rejects browser Origin"
            )
            require_status(
                http(port, "/health", headers={"Sec-Fetch-Site": "same-site"})[0],
                403, f"{role} rejects browser fetch metadata"
            )
            require_status(
                http(port, "/v1/chat/completions", method="OPTIONS")[0],
                403, f"{role} rejects browser CORS preflight"
            )
            chat = {
                "messages": [{"role": "user", "content": "Say hello."}],
                "max_tokens": 5,
                "temperature": 0,
                "stream": False,
                "cache_prompt": False,
            }
            if role == "chat":
                require_status(http(port, "/props")[0], 200, "chat model diagnostics")
                require_status(http(port, "/v1/models")[0], 403, "chat denies model listing")
                require_status(http(port, "/v1/embeddings", "POST",
                                    {"input": "synthetic"})[0], 403, "chat denies embeddings")
                for title, body in (
                    ("tools", {**chat, "tools": []}),
                    ("tool-choice", {**chat, "tool_choice": "auto"}),
                    ("functions", {**chat, "functions": []}),
                    ("cache-true", {**chat, "cache_prompt": True}),
                    ("cache-missing", {k: v for k, v in chat.items() if k != "cache_prompt"}),
                    ("streaming", {**chat, "stream": True}),
                    ("tool-role", {**chat, "messages": [{"role": "tool", "content": "x"}]}),
                    ("tool-message", {**chat, "messages": [
                        {"role": "user", "content": "x", "tool_calls": []}
                    ]}),
                    # Verify that validation after the POST body is read still
                    # rejects malformed structures before model inference.
                    ("non-object-body", []),
                    ("missing-messages", {**chat, "messages": []}),
                    ("non-string-message", {**chat, "messages": [
                        {"role": "user", "content": {"text": "x"}}
                    ]}),
                ):
                    require_status(http(port, "/v1/chat/completions", "POST", body)[0],
                                   403, f"chat denies {title}")
                status, response, response_headers = http(
                    port, "/v1/chat/completions", "POST", chat
                )
                if status != 200:
                    # Synthetic prompt only; expose the actual HTTP rejection
                    # rather than assuming generation or security is at fault.
                    error_text = response.decode("utf-8", errors="replace")[:800]
                    log_tail = logfile.read_text(errors="replace")[-1200:]
                    raise AssertionError(
                        f"chat permits bounded text completion: expected HTTP 200, "
                        f"received {status}; response={error_text!r}; "
                        f"server-log-tail={log_tail!r}"
                    )
                require_status(status, 200, "chat permits bounded text completion")
                profile = next(
                    (value for key, value in response_headers.items()
                     if key.lower() == "x-bv-chat-profile"), None
                )
                if profile != "professional-v1":
                    raise AssertionError("Accepted chat was not tagged with the BV professional behavior profile")
                print("PASS: chat professional behavior profile applied (header attestation)", flush=True)
                if not isinstance(json.loads(response).get("choices"), list):
                    raise AssertionError("Accepted chat response missing choices")
            else:
                require_status(http(port, "/props")[0], 403, "embedding denies chat diagnostics")
                require_status(http(port, "/v1/models")[0], 200, "embedding model identity")
                require_status(http(port, "/v1/chat/completions", "POST", chat)[0],
                               403, "embedding denies chat generation")
                require_status(
                    http(port, "/v1/embeddings", "POST",
                         {"input": "synthetic", "tools": []})[0],
                    403, "embedding denies tool declarations"
                )
                for title, body in (
                    ("non-object-body", []),
                    ("missing-input", {}),
                    ("non-string-input", {"input": {"text": "x"}}),
                ):
                    require_status(
                        http(port, "/v1/embeddings", "POST", body)[0],
                        403, f"embedding denies {title}"
                    )
                status, body, _ = http(port, "/v1/embeddings", "POST",
                                       {"input": "search_document: a synthetic experiment"})
                require_status(status, 200, "embedding permits its single inference endpoint")
                payload = json.loads(body)
                if not isinstance(payload.get("data"), list) or not payload["data"]:
                    raise AssertionError("Accepted embedding response lacks vector rows")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    print(f"PASS: BV inference role {role} complete", flush=True)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: bv_inference_smoke.py /path/to/llama-server")
    binary = Path(sys.argv[1]).resolve()
    if not binary.is_file():
        raise SystemExit(f"Missing inference binary: {binary}")
    with tempfile.TemporaryDirectory(prefix="bv-smoke-") as directory:
        model = expanded_context_smoke_fixture(test_model(directory), directory)
        for role in ("chat", "embedding"):
            exercise(binary, model, role, directory)


if __name__ == "__main__":
    main()
