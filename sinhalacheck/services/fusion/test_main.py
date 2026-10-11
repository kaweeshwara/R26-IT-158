from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import main
from fastapi.testclient import TestClient


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class FakeClient:
    calls = []

    def __init__(self, **_kwargs):
        self.__class__.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, json):
        self.calls.append((url, json))
        if url.endswith("/analyze"):
            return FakeResponse({"source_score": 0.71, "temporal_score": 0.88})
        return FakeResponse({"final_score": 0.74, "label": "CREDIBLE"})


class FakeAnalysisClient:
    def __init__(self, **_kwargs):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, json):
        if url.endswith("/predict"):
            return FakeResponse({
                "content_score": 0.8,
                "label": "CREDIBLE",
                "linguistic_features": {},
                "truncated": False,
                "probabilities": {"NOT_CREDIBLE": 0.2, "CREDIBLE": 0.8},
            })
        raise AssertionError(f"Unexpected module request: {url}")


class FakeSyncClient:
    def __init__(self, **_kwargs):
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def get(self, url):
        self.requests.append(url)
        return FakeResponse({"id2label": {"0": "NOT_CREDIBLE", "1": "CREDIBLE"}})

    def post(self, url, json):
        self.requests.append((url, json))
        return FakeResponse({
            "predictions": [
                {"probabilities": {"NOT_CREDIBLE": 0.2, "CREDIBLE": 0.8}}
                for _ in json["texts"]
            ]
        })


class FakeLimeExplanation:
    def as_list(self, label):
        return [("පුවත", 0.18), ("තහවුරු", -0.07)]


class FakeLimeExplainer:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.explain_options = None

    def explain_instance(self, text, classifier_fn, *, labels, num_features, num_samples):
        classifier_fn([text, "perturbed text"])
        self.explain_options = {
            "labels": labels,
            "num_features": num_features,
            "num_samples": num_samples,
        }
        return FakeLimeExplanation()


class FusionXLMRTests(unittest.TestCase):
    def test_bilingual_lime_uses_module1_and_five_hundred_samples(self):
        lime = FakeLimeExplainer()
        with patch.object(main.httpx, "Client", FakeSyncClient), \
                patch.object(main, "LimeTextExplainer", return_value=lime):
            explanations = main.generate_lime_explanations("මෙය පරීක්ෂණ පුවතකි")

        self.assertEqual(len(explanations), 2)
        self.assertIn("supports", explanations[0]["english"])
        self.assertIn("සහාය", explanations[0]["sinhala"])
        self.assertIn("argues against", explanations[1]["english"])
        self.assertEqual(lime.explain_options["num_samples"], 500)
        self.assertEqual(lime.explain_options["num_features"], 5)

    def test_analyze_keeps_lime_opt_in(self):
        request = main.AnalyzeRequest(text="sample Sinhala claim", explain=True)
        with patch.object(main.httpx, "AsyncClient", FakeAnalysisClient), \
                patch.object(main, "generate_lime_explanations",
                             return_value=[{"word": "claim", "weight": 0.1}]) as lime:
            result = asyncio.run(main.analyze(request))
        lime.assert_called_once_with(request.text)
        self.assertEqual(result["lime_explanations"][0]["word"], "claim")
        self.assertFalse(result["temporal_warning"]["available"])

    def test_api_route_is_additive_and_validates_scores(self):
        with TestClient(main.app) as client:
            routes = {route.path for route in main.app.routes}
            self.assertIn("/analyze", routes)
            self.assertIn("/analyze/xlmr", routes)
            self.assertEqual(client.get("/").status_code, 200)
            response = client.post(
                "/analyze/xlmr",
                json={"text": "claim", "source_score": 1.1},
            )
        self.assertEqual(response.status_code, 422)

    def test_request_scores_forward_without_calling_module2(self):
        request = main.XLMRAnalyzeRequest(
            text="claim", source_score=0.45, temporal_score=0.55
        )
        with patch.object(main.httpx, "AsyncClient", FakeClient):
            result = asyncio.run(main.analyze_xlmr(request))

        self.assertEqual(result["score_source"], "request")
        self.assertIsNone(result["module2"])
        self.assertEqual(len(FakeClient.calls), 1)
        self.assertTrue(FakeClient.calls[0][0].endswith("/predict"))
        self.assertEqual(FakeClient.calls[0][1]["source_score"], 0.45)
        self.assertEqual(FakeClient.calls[0][1]["temporal_score"], 0.55)

    def test_url_uses_module2_scores_before_calling_module3(self):
        request = main.XLMRAnalyzeRequest(
            text="claim",
            url="https://example.lk/news",
            published_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            recirculated=True,
            cross_count=2,
        )
        with patch.object(main.httpx, "AsyncClient", FakeClient):
            result = asyncio.run(main.analyze_xlmr(request))

        self.assertEqual(result["score_source"], "module2")
        self.assertEqual(result["module2"]["source_score"], 0.71)
        self.assertEqual(len(FakeClient.calls), 2)
        module2_payload = FakeClient.calls[0][1]
        self.assertEqual(module2_payload["recirculated"], True)
        module3_payload = FakeClient.calls[1][1]
        self.assertEqual(module3_payload["source_score"], 0.71)
        self.assertEqual(module3_payload["temporal_score"], 0.88)

    def test_invalid_external_score_is_rejected(self):
        with self.assertRaises(ValueError):
            main.XLMRAnalyzeRequest(text="claim", source_score=1.1)


if __name__ == "__main__":
    unittest.main()
