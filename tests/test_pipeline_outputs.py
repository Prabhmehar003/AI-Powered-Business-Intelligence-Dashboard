from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from aibids.config import PROCESSED_DIR  # noqa: E402
from aibids.io_utils import read_csv  # noqa: E402
from aibids.pipeline import run_pipeline  # noqa: E402
from aibids.qa import AnalyticsQA  # noqa: E402


class PipelineOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (PROCESSED_DIR / "forecast_daily.csv").exists():
            run_pipeline()

    def test_forecast_horizon_is_90_days(self):
        rows = read_csv(PROCESSED_DIR / "forecast_daily.csv")
        self.assertEqual(len(rows), 90)

    def test_anomaly_file_has_expected_columns(self):
        rows = read_csv(PROCESSED_DIR / "anomaly_events.csv")
        self.assertTrue(rows)
        self.assertIn("severity", rows[0])
        self.assertIn("action_hint", rows[0])

    def test_qa_answers_forecast_question(self):
        answer = AnalyticsQA().answer("Show the next 30 day forecast")
        self.assertIn("Forecast revenue", answer["answer"])


if __name__ == "__main__":
    unittest.main()
