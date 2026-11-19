import unittest
from ml.training.evaluate import metrics

class EvaluationTests(unittest.TestCase):
    def test_known_matrix(self):
        result = metrics([0, 0, 1, 1], [.1, .8, .2, .9], .5)
        self.assertEqual(result['confusion_matrix'], dict(tn=1, fp=1, fn=1, tp=1))
        self.assertEqual(result['precision'], .5)
        self.assertEqual(result['recall'], .5)
    def test_undefined(self):
        result = metrics([0, 0], [.1, .2], .5)
        self.assertIsNone(result['precision'])
        self.assertIsNone(result['recall'])
        self.assertIsNone(result['roc_auc'])
    def test_invalid(self):
        for labels, scores in [([], []), ([1], [float('nan')]), ([2], [.5])]:
            with self.assertRaises(ValueError):
                metrics(labels, scores, .5)
