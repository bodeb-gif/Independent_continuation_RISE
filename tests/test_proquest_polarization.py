"""Leakage, interpretation and comparability checks for polarization inputs."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_polarization import forecast_months, party_separation, political_months
from proquest_polarization_models import added_inputs, observation_losses, paired_interval


class PolarizationTests(unittest.TestCase):
    def test_party_distance_uses_actual_votes_only(self):
        members = pd.DataFrame({"congress": [56]*12, "chamber": ["House"]*12,
                                "icpsr": range(12), "party_code": [100]*6 + [200]*6})
        votes = members.drop(columns="party_code").assign(rollnumber=1, cast_code=[1]*5+[9]+[6]*5+[2])
        dates = pd.DataFrame({"congress": [56], "chamber": ["House"], "rollnumber": [1], "date": ["1900-01-01"]})
        result, _ = party_separation(votes, members, dates)
        self.assertEqual(result.political_gap.iloc[0], 1.)
        self.assertEqual(result.democratic_votes.iloc[0], 5)
        self.assertEqual(result.republican_votes.iloc[0], 5)
        votes.loc[0, "cast_code"] = 9
        result, _ = party_separation(votes, members, dates)
        self.assertTrue(result.empty)

    def test_reject_ambiguous_party_and_duplicate_votes(self):
        members = pd.DataFrame({"congress": [56,56], "chamber": ["House"]*2,
                                "icpsr": [1,2], "party_code": [100,200]})
        votes = members.drop(columns="party_code").assign(rollnumber=1,cast_code=[1,6])
        dates = pd.DataFrame({"congress": [56], "chamber": ["House"], "rollnumber": [1], "date": ["1900-01-01"]})
        ambiguous = pd.concat([members, members.iloc[[0]].assign(party_code=200)])
        result, audit = party_separation(votes, ambiguous, dates, minimum_party_votes=1)
        self.assertTrue(result.empty)
        self.assertEqual(audit["ambiguous_member_keys"], 1)
        with self.assertRaisesRegex(ValueError, "Duplicate member"):
            party_separation(pd.concat([votes, votes]), members, dates)

    def test_political_reporting_buffer_and_no_future_dependence(self):
        dates = pd.to_datetime(["1898-12-31", "1899-01-01", "1899-12-31", "1900-01-01", "1900-02-01"])
        calls = pd.DataFrame({"date": dates, "political_gap": [1., .2, .4, .9, 1.]})
        # At February publication, January is the reporting buffer.
        origins = pd.period_range("1900-02", periods=1, freq="M")
        first = political_months(calls, origins, minimum_rollcalls=2)
        self.assertAlmostEqual(first.political_polarization.iloc[0], .3)
        calls.loc[calls.date.ge("1900-01-01"), "political_gap"] = 0.
        pd.testing.assert_frame_equal(first, political_months(calls, origins, minimum_rollcalls=2))

    def test_forecast_polarization_is_opposing_camps_not_neutrality(self):
        national = pd.DataFrame({"month": ["1900-01", "1900-02", "1900-03", "1900-04"],
                                 "topic": ["general_business"]*4,
                                 "positive_share": [.5,0,1,1], "negative_share": [.5,0,0,0]})
        support = pd.DataFrame({"origin": ["1900-04"], "disagreement_3m": [.5]})
        result = forecast_months(national, support, pd.period_range("1900-04", periods=1, freq="M"))
        self.assertAlmostEqual(result.forecast_polarization.iloc[0], 1/3)
        national.loc[3, "negative_share"] = 1.
        again = forecast_months(national, support, pd.period_range("1900-04", periods=1, freq="M"))
        pd.testing.assert_frame_equal(result, again)
        support["disagreement_3m"] = np.nan
        self.assertTrue(pd.isna(forecast_months(national, support, pd.period_range("1900-04", periods=1, freq="M")).forecast_polarization.iloc[0]))

    def test_preprocessing_is_training_only(self):
        train = pd.DataFrame({"x": [0.,1.,np.nan], "empty": [np.nan]*3})
        evaluation = pd.DataFrame({"x": [100.,np.nan], "empty": [2.,np.nan]})
        a,b,p = added_inputs(train,evaluation,("x","empty"))
        a2,b2,p2 = added_inputs(train,evaluation.assign(x=99999),("x","empty"))
        np.testing.assert_array_equal(a,a2)
        pd.testing.assert_frame_equal(p,p2)
        self.assertEqual(p.loc[0,"median"],.5)
        self.assertEqual(p.loc[1,"median"],0)
        np.testing.assert_array_equal(b[:,-2:],[[0,0],[1,1]])

    def test_paired_identical_models_have_zero_difference(self):
        interval = paired_interval(np.arange(1977,2011),np.zeros(34))
        self.assertEqual(interval["n_blocks"],7)
        self.assertEqual(interval["improvement"],0)
        self.assertEqual(interval["low"],0)
        self.assertEqual(interval["high"],0)
        b,_ = observation_losses(np.array([0,1,2]), np.full((3,3),1/3))
        np.testing.assert_allclose(b,2/3)


if __name__ == "__main__":
    unittest.main()
