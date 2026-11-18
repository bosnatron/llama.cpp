#!/usr/bin/env python3
"""BOSNATRON privacy regression: no automatic external HTTP in BV inference.

Source contracts exercise the exact checked-out fork. The C++ policy unit is
compiled separately. These tests do not claim that an unbuilt Windows binary
has passed a network packet capture.
"""
import importlib.util
import os
from pathlib import Path
from unittest import TestCase, main, mock

ROOT = Path(__file__).resolve().parents[3]
COMMON_HTTP = ROOT / "common" / "http.h"
SERVER = ROOT / "tools" / "server" / "server.cpp"
SERVER_HTTP = ROOT / "tools" / "server" / "server-http.cpp"
SMOKE = ROOT / "tools" / "server" / "tests" / "bv_inference_smoke.py"


class BVNoTrackingSourceTests(TestCase):
    def test_remote_client_factory_blocked_before_client_construction(self):
        source = COMMON_HTTP.read_text(encoding="utf-8")
        start = source.index("common_http_client(const std::string & url)")
        body = source[start:]
        guard = body.index("bv_refuse_outbound_http_client();")
        client = body.index("httplib::Client cli(")
        self.assertLess(guard, client)
        self.assertIn('#include "bv-inference-network-policy.h"', source)

    def test_bv_server_rejects_remote_metadata_before_resolution(self):
        source = SERVER.read_text(encoding="utf-8")
        start = source.index("static int server_run(common_params")
        body = source[start:]
        guard = body.index("bv_inference_outbound_network_forbidden()")
        resolve = body.index("common_models_handler_init(params")
        self.assertLess(guard, resolve)
        self.assertIn("!params.model.hf_repo.empty()", body[guard:resolve])
        self.assertIn("!params.model.docker_repo.empty()", body[guard:resolve])
        self.assertIn("!params.offline", body[guard:resolve])

    def test_bv_server_disables_cloud_mode_and_external_features(self):
        source = SERVER_HTTP.read_text(encoding="utf-8")
        self.assertIn("bv_role != bv_inference_role::off && gcp.enabled", source)
        self.assertIn("params.server_connect", source)
        self.assertIn("params.ui_mcp_proxy", source)
        self.assertIn("!params.offline", source)
        self.assertIn('"/metrics"', (ROOT / "tools" / "server" / "tests" / "bv_inference_smoke.py").read_text(encoding="utf-8"))

    def test_bv_smoke_uses_preexisting_local_model_only(self):
        source = SMOKE.read_text(encoding="utf-8")
        block = source[source.index("def test_model("):source.index("def expanded_context_smoke_fixture(")]
        self.assertIn('os.environ.get("BV_TEST_MODEL_PATH")', block)
        self.assertIn("hashlib.file_digest", block)
        self.assertNotIn("urllib.request.urlopen", block)
        self.assertNotIn("MODEL_URL", source)
        self.assertNotIn("huggingface.co/", source)

    @staticmethod
    def _load_smoke():
        spec = importlib.util.spec_from_file_location("bv_inference_smoke_privacy_test", SMOKE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_missing_model_does_not_trigger_download(self):
        module = self._load_smoke()
        with mock.patch.dict(os.environ, {"BV_TEST_MODEL_PATH": ""}), \
             mock.patch("urllib.request.urlopen", side_effect=AssertionError("network request forbidden")) as outgoing:
            with self.assertRaisesRegex(RuntimeError, "automatic network model downloads are forbidden"):
                module.test_model(None)
            outgoing.assert_not_called()

    def test_nonexistent_model_does_not_trigger_download(self):
        module = self._load_smoke()
        with mock.patch.dict(os.environ, {"BV_TEST_MODEL_PATH": "/this/path/does/not/exist/model.gguf"}), \
             mock.patch("urllib.request.urlopen", side_effect=AssertionError("network request forbidden")) as outgoing:
            with self.assertRaisesRegex(RuntimeError, "Pinned local test GGUF not found"):
                module.test_model(None)
            outgoing.assert_not_called()


if __name__ == "__main__":
    main()
