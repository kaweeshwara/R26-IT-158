from __future__ import annotations

import unittest

from randomize_groups import allocate_groups


class RandomizeGroupsTests(unittest.TestCase):
    def test_balanced_and_reproducible_allocation(self):
        codes = [f"anon-{index:02d}" for index in range(40)]
        first = allocate_groups(codes, seed=7)
        second = allocate_groups(codes, seed=7)
        counts = {group: sum(row["group"] == group for row in first) for group in ("A", "B")}
        self.assertEqual(counts, {"A": 20, "B": 20})
        self.assertEqual(first, second)

    def test_rejects_invalid_code_list(self):
        with self.assertRaisesRegex(ValueError, "Exactly 40"):
            allocate_groups(["anon-1"])
        codes = [f"anon-{index}" for index in range(39)] + ["anon-0"]
        with self.assertRaisesRegex(ValueError, "unique"):
            allocate_groups(codes)


if __name__ == "__main__":
    unittest.main()
