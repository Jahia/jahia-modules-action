"""The points of system A2, the checks of a factors object, and the comment."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
import scoring  # noqa: E402

REF = 'Jahia/example#1'


def factors(**over):
    base = {'ref': REF, 'security': False, 'impact': 'editorBlocked', 'feature': 'jContent paste',
            'reach': 'high', 'workaround': 'painful', 'regression': True, 'clear': True, 'cloud': False,
            'older_version_only': False, 'customers': 1, 'confidence': 'high',
            'why': 'Editors cannot paste into a named area of a page.'}
    base.update(over)
    return base


class ScoreTest(unittest.TestCase):

    def test_the_worked_example_of_the_documentation_scores_55(self):
        points, _, p1 = scoring.score(factors(), ['customer'])
        self.assertEqual(points, 55)
        self.assertFalse(p1)
        self.assertEqual(scoring.field_value(points, p1), 55)

    def test_a_crash_reported_by_five_customers_takes_the_cap_of_three(self):
        f = factors(impact='unstable', customers=5, regression=False, cloud=True)
        points, rows, p1 = scoring.score(f, ['customer', 'backport'])
        self.assertEqual(points, 40 + 15 + 4 + 15 + 6 + 3)
        self.assertTrue(p1)
        self.assertIn(('Customers', '3', 15), rows)

    def test_a_p1_case_sorts_above_every_other_bug_on_the_board(self):
        weakest_p1 = scoring.field_value(40, True)
        strongest_other = scoring.field_value(30 + 15 + 8 + 5 + 15 + 6 + 3, False)
        self.assertGreater(weakest_p1, strongest_other)

    def test_the_customer_label_gates_the_count(self):
        points_without, rows, _ = scoring.score(factors(customers=4), [])
        self.assertIn(('Customers', 'No customer label', 0), rows)
        points_with, _, _ = scoring.score(factors(customers=0), ['customer'])
        self.assertEqual(points_with - points_without, 5)

    def test_the_cloud_and_regression_labels_count_even_when_the_agent_missed_them(self):
        f = factors(regression=False, cloud=False)
        points, _, _ = scoring.score(f, ['customer', 'cloud', 'regression'])
        self.assertEqual(points, 20 + 15 + 4 + 5 + 5 + 6 + 3)

    def test_an_older_version_only_bug_loses_five(self):
        points, _, _ = scoring.score(factors(older_version_only=True), ['customer'])
        self.assertEqual(points, 50)


class CheckTest(unittest.TestCase):

    def test_valid_factors_have_no_problem(self):
        self.assertEqual(scoring.check(factors(), REF), [])

    def test_an_unknown_value_is_a_problem(self):
        self.assertTrue(scoring.check(factors(impact='blocker'), REF))
        self.assertTrue(scoring.check(factors(reach='huge'), REF))

    def test_a_missing_key_or_a_wrong_type_is_a_problem(self):
        f = factors()
        del f['why']
        self.assertTrue(scoring.check(f, REF))
        self.assertTrue(scoring.check(factors(customers=True), REF))
        self.assertTrue(scoring.check(factors(customers='2'), REF))

    def test_factors_of_another_ticket_are_a_problem(self):
        self.assertTrue(scoring.check(factors(ref='Jahia/example#2'), REF))

    def test_a_list_is_a_problem(self):
        self.assertEqual(scoring.check([factors()], REF), ['not a JSON object'])


class CommentTest(unittest.TestCase):

    def render(self, **over):
        f = factors(**over)
        points, rows, p1 = scoring.score(f, ['customer'])
        return scoring.render_comment('<!-- m -->', points, rows, p1, f, 'Claude Code', 'https://run', '2026-11-20')

    def test_the_comment_opens_with_the_marker_and_shows_the_total(self):
        body = self.render()
        self.assertTrue(body.startswith('<!-- m -->\n'))
        self.assertIn('**🤖 PM score: 55**', body)
        self.assertIn('| **Total** | | **55** |', body)
        self.assertIn('| Impact | Editors blocked | +20 |', body)
        self.assertIn('| Jahia Cloud | No | 0 |', body)

    def test_a_p1_comment_explains_the_board_value(self):
        body = self.render(impact='data')
        self.assertIn('**🤖 PM score: 175**', body)
        self.assertIn('The board value is 100 + 75 points.', body)

    def test_a_low_confidence_asks_for_a_check(self):
        self.assertIn('please check it', self.render(confidence='low'))


if __name__ == '__main__':
    unittest.main()
