"""Time-unit, exact-tail and checkpoint shortcut checks for permutation diagnostics."""
import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from proquest_rnn_permutation import block_swap,holm,month_mapping,added_values,fast_predict
from proquest_rnn import ClaimGRU,neural_probabilities


class PermutationTests(unittest.TestCase):
    def test_exact_tail_includes_identity_and_ties(self):
        y=np.array([0,1]*4); a=y*.8+.1; b=np.full(8,.5)
        result,distribution=block_swap(y,a,b,np.ones(8),np.repeat(range(4),2))
        self.assertEqual(len(distribution),16)
        self.assertEqual(result.query("metric == 'brier'").p_one_sided.iloc[0],1/16)
        same,_=block_swap(y,a,a,np.ones(8),np.repeat(range(4),2))
        np.testing.assert_array_equal(same.p_one_sided,1)

    def test_block_mapping_preserves_order_season_and_all_months(self):
        mapping=month_mapping((2,0,3,1))
        np.testing.assert_array_equal(np.sort(mapping),np.arange(192))
        np.testing.assert_array_equal(mapping%12,np.arange(192)%12)
        np.testing.assert_array_equal(np.diff(mapping.reshape(4,48),axis=1),1)
        with self.assertRaises(ValueError): month_mapping((0,0,1,2))

    def test_holm_monotonic_adjustment(self):
        np.testing.assert_allclose(holm([.06,.04]),[.08,.08])
        np.testing.assert_allclose(holm([1,.7]),[1,1])

    def test_saved_imputation_and_missingness_move_together(self):
        params=pd.DataFrame({'feature':['political_polarization'],'median':[2.],'mean':[1.],'scale':[2.]})
        values=added_values(pd.DataFrame({'political_polarization':[np.nan,5.]}),params,('political_polarization',))
        np.testing.assert_array_equal(values,[[.5,1],[2,0]])

    def test_cached_states_match_direct_network_for_shared_months(self):
        torch.manual_seed(5)
        model=ClaimGRU(2,3,4); model.eval()
        sequence=torch.randn(3,12,2); claim=np.random.default_rng(5).normal(size=(5,1)).astype('float32')
        extra=np.array([[1,0],[2,0],[0,1]],dtype='float32'); codes=np.array([0,0,1,2,2]); donor=np.array([2,0,1])
        with torch.no_grad(): hidden=model.gru(sequence)[1][-1]
        fast=fast_predict([model],[hidden],claim,codes,extra,donor,'all_monthly',('political_polarization',))
        direct=neural_probabilities(model,sequence[donor[codes]],torch.from_numpy(np.column_stack([claim,extra[donor[codes]]])))
        np.testing.assert_allclose(fast,direct,atol=1e-7)


if __name__=='__main__': unittest.main()
