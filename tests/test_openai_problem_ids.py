import unittest

from scripts.allocate_openai_problem_ids import allocate


class NewTargetIdentityTests(unittest.TestCase):
    def setUp(self):
        self.registry = [{'id': 4, 'title': 'Existing problem'},
                         {'id': 30006988, 'title': 'Another existing target'}]
        self.watermark = {'schema_version': 1, 'last_allocated_id': 30006988,
                          'policy': 'Never reuse gaps.'}
        self.proposal = {'proposal_key': 'bounded-case', 'title': 'Restricted new case',
                         'parent_candidate_ids': [4], 'identity_reviewed': True}

    def test_ids_exceed_both_registry_and_reserved_watermark(self):
        assigned, updated = allocate(self.registry, self.watermark, [self.proposal])
        self.assertEqual(assigned[0]['id'], 30006989)
        self.assertFalse(assigned[0]['published'])
        self.assertEqual(updated['last_allocated_id'], 30006989)
        higher = dict(self.watermark, last_allocated_id=30007050)
        assigned, _ = allocate(self.registry, higher, [self.proposal])
        self.assertEqual(assigned[0]['id'], 30007051)
        self.assertEqual(self.registry[0], {'id': 4, 'title': 'Existing problem'})
        self.assertEqual(self.watermark['last_allocated_id'], 30006988)

    def test_duplicate_targets_and_unreviewed_identity_fail(self):
        for proposal in (dict(self.proposal, title='Existing—problem'),
                         dict(self.proposal, identity_reviewed=False),
                         dict(self.proposal, parent_candidate_ids=[999]),
                         dict(self.proposal, id=30006989)):
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                allocate(self.registry, self.watermark, [proposal])
        with self.assertRaises(ValueError):
            allocate(self.registry, self.watermark, [self.proposal, self.proposal])

    def test_assignment_order_is_repeatable_and_empty_input_consumes_no_ids(self):
        second = dict(self.proposal, proposal_key='other', title='A separate new case')
        first, updated = allocate(self.registry, self.watermark, [second, self.proposal])
        repeat, _ = allocate(self.registry, self.watermark, [self.proposal, second])
        self.assertEqual(first, repeat)
        empty, unchanged = allocate(self.registry, self.watermark, [])
        self.assertFalse(empty)
        self.assertEqual(unchanged, self.watermark)

    def test_malformed_proposals_fail_before_sorting_or_allocation(self):
        for proposal in (None, [], 'target', dict(self.proposal, proposal_key=42)):
            with self.subTest(proposal=proposal), self.assertRaises(ValueError):
                allocate(self.registry, self.watermark, [proposal])
        self.assertEqual(self.watermark['last_allocated_id'], 30006988)


if __name__ == '__main__':
    unittest.main()
