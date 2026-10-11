from __future__ import annotations

import unittest

import torch
from fastapi.testclient import TestClient

import main


class FakeTokenizer:
    def __call__(self, texts, **_kwargs):
        return {"input_ids": torch.ones((len(texts), 2), dtype=torch.long)}


class FakeModel:
    def __call__(self, **inputs):
        rows = inputs["input_ids"].shape[0]
        return type("Output", (), {"logits": torch.tensor([[0.0, 2.0]]).repeat(rows, 1)})()


class Module1BatchTests(unittest.TestCase):
    def setUp(self):
        main.state.update(
            tokenizer=FakeTokenizer(),
            model=FakeModel(),
            device=torch.device("cpu"),
            credible_idx=1,
            id2label={0: "NOT_CREDIBLE", 1: "CREDIBLE"},
            source="test-model",
        )

    def tearDown(self):
        main.state.clear()

    def test_batch_api_returns_aligned_model_probabilities(self):
        client = TestClient(main.app)
        response = client.post(
            "/predict/batch",
            json={"texts": ["Sinhala claim", "modified Sinhala claim"]},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["predictions"]
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["label"], "CREDIBLE")
        self.assertGreater(payload[0]["content_score"], 0.8)
        self.assertAlmostEqual(
            sum(payload[0]["probabilities"].values()), 1.0, places=6
        )

    def test_batch_api_limits_request_size(self):
        client = TestClient(main.app)
        response = client.post("/predict/batch", json={"texts": ["claim"] * 65})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
