"""Check paired precision bounds and conservative treatment of failed calls."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from proquest_reverify_comparison import metrics, field_metrics, field_comparison


class ComparisonTests(unittest.TestCase):
    @staticmethod
    def rows(*pairs):
        return [dict(reviewer1_decision=label, new_keep=keep) for label, keep in pairs]

    def test_failed_call_is_retained_and_filtering_losses_are_counted(self):
        rows = self.rows(('include', True), ('include', False),
                         ('exclude', False), ('exclude', None))
        result = metrics(rows, 'reviewer1')
        self.assertEqual(result['kept_n'], 2)
        self.assertEqual(result['human_valid_lost_n'], 1)
        self.assertEqual(result['human_invalid_removed_n'], 1)
        self.assertEqual(result['after_precision_bounds'], [0.5, 0.5])
        self.assertEqual(result['human_valid_retention'], 0.5)

    def test_unclear_label_uses_paired_assignment_when_dropped(self):
        result = metrics(self.rows(('include', True), ('exclude', False),
                                   ('unclear', False)), 'reviewer1')
        lower, upper = result['precision_change_pp_bounds']
        self.assertAlmostEqual(lower, 100 / 3)
        self.assertAlmostEqual(upper, 200 / 3)
        self.assertEqual(result['after_precision_bounds'], [1, 1])

    def test_unclear_label_uses_paired_assignment_when_kept(self):
        result = metrics(self.rows(('include', True), ('exclude', False),
                                   ('unclear', True)), 'reviewer1')
        lower, upper = result['precision_change_pp_bounds']
        self.assertAlmostEqual(lower, 100 / 6)
        self.assertAlmostEqual(upper, 100 / 3)

    def test_no_retained_claims_has_no_precision(self):
        result = metrics(self.rows(('include', False), ('exclude', False)), 'reviewer1')
        self.assertEqual(result['after_precision_bounds'], [None, None])
        self.assertEqual(result['precision_change_pp_bounds'], [None, None])
        self.assertEqual(result['human_valid_retention'], 0)

    @staticmethod
    def labeled(machine, human, keep=True, decision='include', uncertain=False, incompatible=False):
        return {'machine':{'direction':machine,'current_state':machine},
                'reviewer1':{'direction':human,'current_state':human},
                'reviewer2':{'direction':human,'current_state':human},
                'reviewer1_decision':decision,'reviewer2_decision':decision,
                'reviewer2_field_status':{'direction':'uncertain'} if uncertain else {},
                'reviewer1_current_state_incompatible':incompatible,'new_keep':keep}

    def test_label_filter_improvement_and_loss_of_correct_labels(self):
        rows=[self.labeled('up','up'), self.labeled('up','down',False),
              self.labeled('down','down',False),self.labeled('up','up',decision='exclude')]
        result=field_comparison(rows,'reviewer1')['direction']
        self.assertEqual(result['before']['denominator'],3)
        self.assertEqual(result['after']['denominator'],1)
        self.assertAlmostEqual(result['agreement_change_pp'],100/3)
        self.assertEqual(result['correct_labels_removed_n'],1)
        up=next(c for c in result['before']['per_label'] if c['label']=='up')
        self.assertEqual((up['tp'],up['fp'],up['fn']),(1,1,0))
        self.assertEqual(up['precision'],.5)

    def test_missing_uncertain_and_na_denominators(self):
        rows=[self.labeled(None,None),self.labeled('up','up',uncertain=True),
              self.labeled('NA','NA',keep=None)]
        result=field_metrics(rows,'reviewer2','direction')
        self.assertEqual((result['matches'],result['denominator']),(1,3))
        self.assertEqual(result['per_label_resolved_n'],1)
        self.assertEqual(result['per_label'][0]['label'],'NA')
        self.assertEqual(field_comparison(rows,'reviewer2')['direction']['after']['denominator'],3)

    def test_incompatible_convention_excluded_only_for_reviewer1_current_state(self):
        rows=[self.labeled('up','up',incompatible=True)]
        self.assertEqual(field_metrics(rows,'reviewer1','current_state')['denominator'],0)
        self.assertEqual(field_metrics(rows,'reviewer1','direction')['denominator'],1)
        self.assertEqual(field_metrics(rows,'reviewer2','current_state')['denominator'],1)


if __name__ == '__main__':
    unittest.main()
