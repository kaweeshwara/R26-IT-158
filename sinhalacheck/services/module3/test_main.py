from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import torch

import main


class FakeTokenizer:
    def __call__(self, texts, **_kwargs):
        return {"input_ids": torch.ones((len(texts), 2), dtype=torch.long)}


class FakeModel:
    def __call__(self, **inputs):
        logits = torch.tensor([[0.0, 3.0, 1.0]])
        return SimpleNamespace(logits=logits.repeat(inputs["input_ids"].shape[0], 1))


class FakeExplanation:
    def as_list(self, label):
        return [(f"class-{label}-token", 0.125)]


class FakeExplainer:
    def __init__(self, **kwargs):
        self.class_names = kwargs["class_names"]

    def explain_instance(self, text, predictor, **kwargs):
        self.probabilities = predictor([text])
        self.options = kwargs
        return FakeExplanation()


class Module3Tests(unittest.TestCase):
    def test_class_indices_follow_checkpoint_labels(self):
        checkpoint = SimpleNamespace(
            config=SimpleNamespace(
                num_labels=3,
                id2label={"0": "PARTIAL/FALSE", "1": "CREDIBLE", "2": "UNCERTAIN"},
            )
        )
        self.assertEqual(
            main._class_indices(checkpoint),
            {"partial_false": 0, "credible": 1, "uncertain": 2},
        )

    def test_generic_labels_use_documented_order(self):
        checkpoint = SimpleNamespace(
            config=SimpleNamespace(
                num_labels=3,
                id2label={0: "LABEL_0", 1: "LABEL_1", 2: "LABEL_2"},
            )
        )
        self.assertEqual(
            main._class_indices(checkpoint),
            {"credible": 0, "uncertain": 1, "partial_false": 2},
        )

    def test_prediction_shape_fusion_and_lime_class_order(self):
        main.state.update(
            tokenizer=FakeTokenizer(),
            model=FakeModel(),
            class_indices={"partial_false": 0, "credible": 1, "uncertain": 2},
        )
        explainer = FakeExplainer(class_names=list(main.CLASS_NAMES))
        try:
            with patch.object(main, "LimeTextExplainer", return_value=explainer):
                result = main.predict(
                    main.PredictionRequest(
                        text="මේ පුවත විමසන්න",
                        source_score=0.7,
                        temporal_score=0.9,
                    )
                )
        finally:
            main.state.clear()

        self.assertEqual(
            set(result),
            {"final_score", "label", "model_prediction", "breakdown", "lime_explanations"},
        )
        self.assertEqual(list(result["model_prediction"]), [
            "credible", "uncertain", "partial_false"
        ])
        self.assertGreater(result["model_prediction"]["credible"], 0.8)
        expected_score = (
            0.5 * result["model_prediction"]["credible"]
            + 0.3 * 0.7
            + 0.2 * 0.9
        )
        self.assertAlmostEqual(result["final_score"], round(expected_score, 3))
        self.assertEqual(result["breakdown"]["source"], 0.7)
        self.assertEqual(explainer.class_names, list(main.CLASS_NAMES))
        self.assertEqual(explainer.probabilities.shape, (1, 3))
        self.assertEqual(result["lime_explanations"][0]["word"], "class-0-token")

    def test_verdict_thresholds(self):
        self.assertEqual(main._verdict(0.61), "CREDIBLE")
        self.assertEqual(main._verdict(0.41), "UNCERTAIN")
        self.assertEqual(main._verdict(0.409), "MISINFORMATION")


if __name__ == "__main__":
    unittest.main()
