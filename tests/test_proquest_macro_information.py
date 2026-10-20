"""Vintage timing, revisions, common support, and training-only model checks."""
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from proquest_macro_information import (CLASSES, FEATURES, MODELS, evaluate, fit_study,
                                        load_spec, standardize, training_labels)
from proquest_vintages import (CORE_FEATURES, VintageSeries, macro_features,
                               read_vintage_workbook, vintage_date)


def fixture():
    months = pd.period_range("1979-01", "1999-11", freq="M")
    production = 100 + 10 * np.sin(np.arange(len(months)) / 8)
    matrix = pd.DataFrame({"IPT99M12": production, "IPT00M1": production * 2}, index=months)
    archive = VintageSeries("IPT", matrix)
    origins = pd.period_range("1980-01", "2000-12", freq="M")
    data = pd.DataFrame({"origin": origins, "target": [CLASSES[i % 3] for i in range(len(origins))],
                         **{f: np.cos(np.arange(len(origins)) / (i + 2)) for i, f in enumerate(CORE_FEATURES + FEATURES)}})
    spec, _ = load_spec()
    study = {"name": "fixture", "training_start": "1980-01", "evaluation_start": "2000-01",
             "evaluation_end": "2000-12", "minimum_training_months": 60, "include_cpi": False}
    return data, archive, spec, study


class VintageChecks(unittest.TestCase):
    def test_availability_bounds(self):
        self.assertEqual(vintage_date("IPT62M11"), pd.Timestamp("1962-11-30"))
        self.assertEqual(vintage_date("RUC65Q4"), pd.Timestamp("1965-11-15"))
        self.assertEqual(vintage_date("CPI00Q1"), pd.Timestamp("2000-02-15"))
        with self.assertRaises(ValueError):
            vintage_date("IPT99M13")

    def test_future_and_empty_vintages_are_not_used(self):
        matrix = pd.DataFrame({"RUC99Q4": [4., 5.], "RUC00Q1": [99., 99.], "RUC00Q2": [np.nan, np.nan]},
                              index=pd.period_range("1999-09", "1999-10", freq="M"))
        archive = VintageSeries("RUC", matrix)
        self.assertEqual(archive.snapshot("2000-02")[0], "RUC99Q4")
        self.assertEqual(archive.snapshot("2000-03")[0], "RUC00Q1")
        self.assertEqual(archive.snapshot("2000-06")[0], "RUC00Q1")
        self.assertEqual(archive.snapshot("1999-11"), (None, None))

    def test_growth_is_within_vintage_and_age_tracks_stale_data(self):
        months = pd.period_range("1998-10", "1999-10", freq="M")
        original = np.arange(100., 113.)
        matrix = pd.DataFrame({"IPT99M11": original, "IPT99M12": original * 10}, index=months)
        archive = VintageSeries("IPT", matrix)
        features = macro_features({"IPT": archive}, pd.period_range("1999-12", "2000-01", freq="M"))
        np.testing.assert_allclose(features.ip_growth_12m, 12.)
        self.assertEqual(features.ip_age_months.tolist(), [2, 3])
        self.assertFalse(features.core_available.any())
        matrix.loc[months[-4], "IPT99M12"] = np.nan
        missing = macro_features({"IPT": VintageSeries("IPT", matrix)}, pd.period_range("2000-01", "2000-01", freq="M"))
        self.assertTrue(np.isnan(missing.ip_growth_3m.iloc[0]))

    def test_current_observation_in_snapshot_rejected(self):
        archive = VintageSeries("IPT", pd.DataFrame({"IPT99M12": [100.]}, index=pd.PeriodIndex(["2000-01"], freq="M")))
        with self.assertRaisesRegex(ValueError, "current/future"):
            macro_features({"IPT": archive}, pd.period_range("2000-01", "2000-01", freq="M"))

    def test_raw_xlsx_parser_keeps_gaps_and_excludes_future_vintages(self):
        ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "source.xlsx"
            with ZipFile(path, "w") as archive:
                archive.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="IPT" sheetId="1" r:id="rId1"/></sheets></workbook>')
                archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
                archive.writestr("xl/worksheets/sheet1.xml", f'''<worksheet xmlns="{ns}"><sheetData>
<row r="1"><c r="A1" t="inlineStr"><is><t>DATE</t></is></c><c r="B1" t="inlineStr"><is><t>IPT99M12</t></is></c><c r="C1" t="inlineStr"><is><t>IPT00M1</t></is></c></row>
<row r="2"><c r="A2" t="inlineStr"><is><t>1999:10</t></is></c><c r="B2"><v>100</v></c><c r="C2"><v>999</v></c></row>
<row r="3"><c r="A3" t="inlineStr"><is><t>1999:11</t></is></c><c r="C3"><v>999</v></c></row>
</sheetData></worksheet>''')
            before = path.read_bytes()
            matrix = read_vintage_workbook(path, "IPT", cutoff="2000-01-01")
            self.assertEqual(matrix.columns.tolist(), ["IPT99M12"])
            self.assertEqual(matrix.iloc[0, 0], 100.)
            self.assertTrue(np.isnan(matrix.iloc[1, 0]))
            self.assertEqual(before, path.read_bytes())


class ModelChecks(unittest.TestCase):
    def test_label_maturity_threshold_and_missing_endpoints(self):
        spec, _ = load_spec()
        data = pd.DataFrame({"origin": pd.PeriodIndex(["1999-03", "1999-04", "1999-05"], freq="M")})
        matrix = pd.DataFrame({"IPT99M12": [100., 102., 100., 110.]},
                              index=pd.PeriodIndex(["1999-03", "1999-09", "1999-04", "1999-10"], freq="M"))
        labels = training_labels(data, pd.Period("2000-01", "M"), VintageSeries("IPT", matrix), spec)
        self.assertTrue(pd.isna(labels.training_target.iloc[0]))
        self.assertEqual(labels.exclusion.iloc[0], "missing vintage endpoints")
        self.assertEqual(labels.training_target.iloc[1], "flat")
        self.assertEqual(labels.exclusion.iloc[2], "unmatured")

    def test_future_revisions_and_final_truth_cannot_change_predictions(self):
        data, archive, spec, study = fixture()
        original = fit_study(data, archive, spec, study)["predictions"]
        data["target"] = "fall"
        archive.matrix["IPT00M1"] = 1e9
        revised = fit_study(data, archive, spec, study)["predictions"]
        columns = [f"{m}_{c}" for m in MODELS for c in CLASSES]
        np.testing.assert_allclose(original[columns], revised[columns])

    def test_common_support_and_recent_base_rate(self):
        data, archive, spec, study = fixture()
        data.loc[data.origin == pd.Period("2000-03", "M"), FEATURES[0]] = np.nan
        result = fit_study(data, archive, spec, study)
        self.assertEqual(len(result["predictions"]), 11)
        self.assertEqual(result["annual_refits"].recent_base_rate_months.iloc[0], 120)
        used = result["training_label_audit"].query("used").sort_values("origin").tail(120)
        for label in CLASSES:
            expected = ((used.training_target == label).sum() + 1) / 123
            np.testing.assert_allclose(result["predictions"][f"recent_base_rate_{label}"], expected)
        self.assertTrue(result["predictions"][[f"{m}_{c}" for m in MODELS for c in CLASSES]].notna().all().all())

    def test_scaling_is_fitted_on_training_only(self):
        train = pd.DataFrame({"x": [1., 3.]})
        test = pd.DataFrame({"x": [1e12]})
        x, _, params = standardize(train, test, ("x",))
        self.assertEqual(params["mean"].iloc[0], 2.)
        self.assertEqual(params.scale.iloc[0], 1.)
        np.testing.assert_allclose(x[:, 0], [-1., 1.])

    def test_absent_training_class_excludes_year_for_every_model(self):
        data, archive, spec, study = fixture()
        archive.matrix["IPT00M12"] = archive.matrix["IPT99M12"].copy()
        archive.matrix["IPT99M12"] = 100.
        archive = VintageSeries("IPT", archive.matrix)
        extension = data.tail(12).copy()
        extension["origin"] += 12
        data = pd.concat([data, extension], ignore_index=True)
        result = fit_study(data, archive, spec, {**study, "evaluation_end": "2001-12"})
        self.assertEqual(result["predictions"].origin.min(), pd.Period("2001-01", "M"))
        omitted = result["support_audit"][result["support_audit"].origin.dt.year == 2000]
        self.assertFalse(omitted.evaluated.any())
        self.assertTrue(omitted.refit_exclusion.eq("training history lacks a class").all())
        self.assertEqual(result["annual_refits"].n_evaluation_months.tolist(), [0, 12])
        self.assertFalse(result["training_label_audit"].query("refit_year == 2000").used.any())

    def test_paired_intervals_use_identical_months(self):
        spec, _ = load_spec()
        data = pd.DataFrame({"origin": pd.period_range("2000-01", "2010-12", freq="M"),
                             "target": [CLASSES[i % 3] for i in range(132)]})
        for model in MODELS:
            for label in CLASSES:
                data[f"{model}_{label}"] = 1 / 3
        study = {"evaluation_start": "2000-01", "evaluation_end": "2010-12"}
        result = evaluate(data, {**spec, "bootstrap_draws": 100}, study)
        np.testing.assert_allclose(result["paired_intervals"][["improvement", "low", "high"]], 0.)
        np.testing.assert_allclose(result["leave_block_out"].improvement, 0.)


if __name__ == "__main__":
    unittest.main()
