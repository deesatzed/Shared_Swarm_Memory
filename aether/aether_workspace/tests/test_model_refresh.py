import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

import openrouter_adapter as adapter


class ModelRefreshTests(unittest.TestCase):
    def client(self, handler, **overrides):
        config = adapter.OpenRouterConfig(api_key="test-key", max_retries=1, **overrides)
        client = adapter.OpenRouterFrozenLLM(config)
        client._client.close()
        client._client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        return client

    def test_defaults_separate_text_decisions_and_embeddings(self):
        config = adapter.OpenRouterConfig(api_key="test-key")
        self.assertEqual(config.default_model, "deepseek/deepseek-v4.1-flash-1017")
        self.assertEqual(config.fallback_models, ["nvidia/nemotron-3.5-super-vl", "google/gemini-4-argon"])
        self.assertEqual(config.decision_models, ["liquid/d1-ultra", "typesafe/jev-1.14"])
        self.assertEqual(config.embedding_models, ["google/gemini-embedding-2", "liquid/lfm-2.5-embedding-350m:free"])

    def test_text_request_contains_only_text_models(self):
        seen = []
        def handle(request):
            seen.append((request.url.path, json.loads(request.content)))
            return httpx.Response(200, json={"model": "deepseek/deepseek-v4.1-flash-1017", "choices": [{"message": {"content": "AETHER_OK"}}], "usage": {"prompt_tokens": 8, "completion_tokens": 3}})
        client = self.client(handle)
        self.assertEqual(client.generate("Be concise.", "Return AETHER_OK."), "AETHER_OK")
        path, body = seen[0]
        self.assertEqual(path, "/api/v1/chat/completions")
        self.assertEqual(body["models"], ["deepseek/deepseek-v4.1-flash-1017", "nvidia/nemotron-3.5-super-vl", "google/gemini-4-argon"])
        self.assertEqual(client.last_model, "deepseek/deepseek-v4.1-flash-1017")

    def test_decisions_use_typed_endpoint_and_preserve_probabilities(self):
        self.assertTrue(hasattr(adapter.OpenRouterFrozenLLM, "decide"), "Typed decision requests are missing")
        seen = []
        answer = {"type": "choice", "choice": "green", "probabilities": {"green": 0.98, "red": 0.02}}
        def handle(request):
            seen.append((request.url.path, json.loads(request.content)))
            return httpx.Response(200, json={"model": "liquid/d1-ultra", "answers": {"color": answer}, "usage": {"input_tokens": 10}})
        client = self.client(handle)
        questions = {"color": {"type": "choice", "instructions": "Which color is named?", "criteria": {"green": "green", "red": "red"}}}
        result = client.decide("The color is green.", questions)
        self.assertEqual(result["answers"]["color"], answer)
        self.assertEqual(seen[0][0], "/api/v1/systemone")
        self.assertEqual(seen[0][1]["model"], "liquid/d1-ultra")
        self.assertNotIn("messages", seen[0][1])

    def test_decision_failure_tries_only_other_decision_model(self):
        self.assertTrue(hasattr(adapter.OpenRouterFrozenLLM, "decide"), "Typed decision requests are missing")
        models = []
        def handle(request):
            model = json.loads(request.content)["model"]
            models.append(model)
            if len(models) == 1:
                return httpx.Response(503, json={"error": {"message": "unavailable"}})
            return httpx.Response(200, json={"model": model, "answers": {"ok": {"type": "noul", "noul": 0.9}}})
        result = self.client(handle).decide("green", {"ok": {"type": "noul", "instructions": "Is it green?"}})
        self.assertEqual(models, ["liquid/d1-ultra", "typesafe/jev-1.14"])
        self.assertEqual(result["model"], "typesafe/jev-1.14")

    def test_embeddings_use_explicit_model_without_automatic_fallback(self):
        self.assertTrue(hasattr(adapter.OpenRouterFrozenLLM, "embed"), "Embedding requests are missing")
        seen = []
        def handle(request):
            seen.append((request.url.path, json.loads(request.content)))
            return httpx.Response(200, json={"model": "google/gemini-embedding-2", "data": [{"index": 0, "embedding": [0.1, 0.2]}]})
        result = self.client(handle).embed(["Aether connection check."])
        self.assertEqual(result["data"][0]["embedding"], [0.1, 0.2])
        self.assertEqual(seen[0][0], "/api/v1/embeddings")
        self.assertEqual(seen[0][1]["model"], "google/gemini-embedding-2")
        self.assertNotIn("models", seen[0][1])

    def test_embedding_failure_does_not_switch_vector_spaces(self):
        self.assertTrue(hasattr(adapter.OpenRouterFrozenLLM, "embed"), "Embedding requests are missing")
        models = []
        def handle(request):
            models.append(json.loads(request.content)["model"])
            return httpx.Response(503, json={"error": {"message": "unavailable"}})
        with self.assertRaises(RuntimeError):
            self.client(handle).embed(["connection check"])
        self.assertEqual(models, ["google/gemini-embedding-2"])

    def test_key_file_reads_only_requested_key_without_shell_execution(self):
        import inspect
        self.assertIn("credentials_file", inspect.signature(adapter.build_llm_client).parameters)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "merged.env"
            marker = Path(td) / "should-not-exist"
            path.write_text(f"OTHER_SECRET=private\nMODEL1=unapproved-model\nexport OPENROUTER_API_KEY='test-file-key' # comment\nRUN=$(touch {marker})\n")
            with patch.dict(os.environ, {}, clear=True):
                client = adapter.build_llm_client(credentials_file=path)
                self.addCleanup(client.close)
                self.assertEqual(client.config.api_key, "test-file-key")
                self.assertEqual(client.config.default_model, "deepseek/deepseek-v4.1-flash-1017")
                self.assertNotIn("OTHER_SECRET", os.environ)
                self.assertFalse(marker.exists())
                self.assertNotIn("test-file-key", repr(client.config))

    def test_missing_explicit_key_file_does_not_silently_use_mock(self):
        import inspect
        self.assertIn("credentials_file", inspect.signature(adapter.build_llm_client).parameters)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises((FileNotFoundError, ValueError)):
                adapter.build_llm_client(credentials_file="/missing/aether.env")

    def test_cli_can_import_and_uses_current_default(self):
        try:
            cli = importlib.import_module("aether_cli2")
        except ImportError:
            self.fail("The CLI must import before its model settings can be used")
        import inspect
        self.assertIsNone(inspect.signature(cli.AetherWorkspace.load_domain_runtime).parameters["model_name"].default)

    def test_standard_cli_exposes_the_runner(self):
        path = Path(__file__).resolve().parents[1] / "aether_cli.py"
        result = subprocess.run([sys.executable, "-B", str(path), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout)
        self.assertIn("run", result.stdout)

    def test_explicit_environment_model_selection_stays_within_its_api_group(self):
        with patch.dict(os.environ, {"MODEL1": "google/gemini-4-argon", "DECISION_MODEL": "typesafe/jev-1.14", "EMBED_MODEL": "liquid/lfm-2.5-embedding-350m:free"}):
            config = adapter.OpenRouterConfig(api_key="test-key")
            self.assertEqual(config.default_model, "google/gemini-4-argon")
            self.assertEqual(config.decision_models, ["typesafe/jev-1.14", "liquid/d1-ultra"])
            self.assertEqual(config.embedding_models, ["liquid/lfm-2.5-embedding-350m:free", "google/gemini-embedding-2"])

    def test_invalid_decision_response_is_not_treated_as_approval(self):
        self.assertTrue(hasattr(adapter.OpenRouterFrozenLLM, "decide"))
        client = self.client(lambda request: httpx.Response(200, json={"answers": {}}))
        with self.assertRaises(RuntimeError):
            client.decide("green", {"ok": {"type": "noul", "instructions": "Is it green?"}})

    def test_auth_failure_does_not_try_more_models_or_expose_response_secrets(self):
        seen = []
        def handle(request):
            seen.append(request)
            return httpx.Response(401, json={"error": {"message": "test-secret-in-upstream-message"}})
        with self.assertRaises(RuntimeError) as caught:
            self.client(handle).decide("green", {"ok": {"type": "noul", "instructions": "Is it green?"}})
        self.assertEqual(len(seen), 1)
        self.assertNotIn("test-secret", str(caught.exception))

    def test_bootstrap_emits_compilable_current_model_clients(self):
        source = Path(__file__).resolve().parents[1]
        packager = source / "scripts/package_aether.py"
        self.assertTrue(packager.exists(), "A safe current-model packager is missing")
        with tempfile.TemporaryDirectory() as td:
            destination = Path(td)
            built = subprocess.run([sys.executable, "-B", str(packager), "--output", str(destination)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            emitted = destination / "bootstrap-test"
            generated = subprocess.run([sys.executable, "-B", str(destination / "aether_setup.py"), "--output", str(emitted)], capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            for path in emitted.rglob("*.py"):
                compile(path.read_text(), str(path), "exec")
            self.assertEqual((emitted / "model_config.py").read_text(), (source / "model_config.py").read_text())
            self.assertFalse((emitted / ".env").exists())
            self.assertFalse((emitted / "merged.env").exists())


if __name__ == "__main__":
    unittest.main()
