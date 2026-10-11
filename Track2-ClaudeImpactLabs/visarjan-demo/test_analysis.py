"""Tests for missing-event coverage, ranking and recovery semantics."""
import unittest
from server import analyze, WORKSPACE
from test_server import record, as_csv


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full = analyze((WORKSPACE/'impactdata/bhopal_ghats_2023_2025.csv').read_text(encoding='utf-8-sig'))

    def test_full_coverage_and_missing_events(self):
        view = self.full['model']['views']['all|all']
        self.assertEqual((view['site_count'], view['event_count'], view['expected'], view['assessed']), (7, 6, 378, 343))
        durga = self.full['model']['views']['2025|Durga']
        missing = [g for g in durga['sites'] if g['absent_events']]
        self.assertEqual(len(missing), 2)
        self.assertEqual(durga['expected'], 63)
        for g in missing:
            self.assertEqual((g['assessed'], g['missing'], g['pollution_rank']), (0, 9, None))
        self.assertEqual(set(durga['testing_order'][:2]), {g['site'] for g in missing})

    def test_no_lookahead_in_latest_evidence(self):
        data = analyze(as_csv([record(year='2023', site='A', value=''), record(year='2025', site='A'), record(year='2023', site='B')]))
        g = next(g for g in data['model']['views']['2023|Ganesh']['sites'] if g['site']=='A')
        self.assertIsNone(g['latest_year'])

    def test_recovery_requires_during_and_after_readings(self):
        cases = [(8, 2, 'Returned within reference'), (8, 5, 'Still outside reference'),
                 (2, 2, 'Within reference during and after'), ('', 2, 'After within reference; during unavailable'),
                 (8, '', 'After reading unavailable'), ('', 8, 'Outside reference after immersion')]
        for during, after, expected in cases:
            with self.subTest(during=during, after=after):
                data = analyze(as_csv([record(phase='during', value=during), record(phase='after', value=after)]))
                event = data['model']['views']['all|all']['sites'][0]['events'][0]
                check = next(r for r in event['recovery'] if r['parameter']=='BOD')
                self.assertEqual(check['status'], expected)
                self.assertIsNone(check['before_after_delta'])

    def test_before_after_change_does_not_require_during(self):
        data = analyze(as_csv([record(phase='pre', value=8), record(phase='after', value=2)]))
        event = data['model']['views']['all|all']['sites'][0]['events'][0]
        self.assertEqual(event['before_after_pairs'], 1)
        check = next(r for r in event['recovery'] if r['parameter']=='BOD')
        self.assertEqual(check['before_after_delta'], -6)
        self.assertEqual(check['status'], 'After within reference; during unavailable')

    def test_repeated_breaches_and_ties(self):
        rows = [record(site=site, phase=phase, value=8) for site in ['A','B'] for phase in ['during','after']]
        data = analyze(as_csv(rows))
        groups = data['model']['views']['all|all']['sites']
        for g in groups:
            self.assertEqual(g['persistent_pairs'], 1)
            self.assertEqual(g['pollution_rank'], 1)
            self.assertEqual(g['testing_rank'], 1)

    def test_pollution_and_testing_answer_different_questions(self):
        rows = [record(site='Polluted', phase=p, parameter=parameter, value=8 if parameter!='pH' else 7,
                       unit_assumed='' if parameter=='pH' else 'mg/l')
                for p in ['pre','during','after'] for parameter in ['pH','BOD','Dissolved oxygen']]
        rows += [record(site='Untested', value='', flag='not sampled')]
        view = analyze(as_csv(rows))['model']['views']['all|all']
        self.assertEqual(view['pollution_order'][0], 'Polluted')
        self.assertEqual(view['testing_order'][0], 'Untested')
        self.assertIsNone(next(g for g in view['sites'] if g['site']=='Untested')['pollution_rank'])

    def test_brief_uses_actual_years_and_unmatched_evidence(self):
        view = analyze(as_csv([record(year='2026', value=8)]))['model']['views']['all|all']
        self.assertIn('2026', view['brief_en'])
        self.assertNotIn('2023–2025', view['brief_en'])
        self.assertIn('not matched', view['brief_en'])
        self.assertIn('कोलीफॉर्म', view['brief_hi'])

    def test_low_oxygen_precedes_any_bod_only_breach(self):
        data = analyze(as_csv([record(site='Zero oxygen', parameter='Dissolved oxygen', value=0),
                              record(site='Low oxygen', parameter='Dissolved oxygen', value=4.9),
                              record(site='High BOD', value=300), record(site='Missing oxygen', parameter='Dissolved oxygen', value='', flag='BDL')]))
        view = data['model']['views']['all|all']
        self.assertEqual(view['pollution_order'], ['Zero oxygen', 'Low oxygen', 'High BOD', 'Missing oxygen'])

    def test_bundled_hindi_brief_contains_no_generated_english(self):
        for view in self.full['model']['views'].values():
            self.assertNotRegex(view['brief_hi'], r'[A-Za-z]')


if __name__ == '__main__':
    unittest.main()
