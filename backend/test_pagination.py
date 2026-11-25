"""
Integration tests for Transaction Pagination (Max 15 per page).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from httpx import AsyncClient, ASGITransport
from main import app
from database.connection import engine


class TestTransactionPagination(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=transport, base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        await engine.dispose()

    async def test_default_pagination_limits_to_15(self):
        """Verify GET /api/transactions defaults to page 1 and at most 15 items."""
        response = await self.client.get("/api/transactions")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("transactions", data)
        self.assertIn("pagination", data)
        self.assertIn("stats", data)

        pagination = data["pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["limit"], 15)
        self.assertFalse(pagination["has_prev"])

        # Must not exceed 15 items per page
        self.assertLessEqual(len(data["transactions"]), 15)

        total = pagination["total"]
        expected_pages = math.ceil(total / 15) if total > 0 else 1
        self.assertEqual(pagination["total_pages"], expected_pages)

        if expected_pages > 1:
            self.assertTrue(pagination["has_next"])
        else:
            self.assertFalse(pagination["has_next"])

    async def test_page_navigation_and_item_uniqueness(self):
        """Verify navigation across pages produces unique items without overlap."""
        # Page 1
        res1 = await self.client.get("/api/transactions?page=1&limit=15")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()

        if data1["pagination"]["total_pages"] >= 2:
            # Page 2
            res2 = await self.client.get("/api/transactions?page=2&limit=15")
            self.assertEqual(res2.status_code, 200)
            data2 = res2.json()

            self.assertEqual(data2["pagination"]["page"], 2)
            self.assertEqual(data2["pagination"]["limit"], 15)
            self.assertTrue(data2["pagination"]["has_prev"])

            ids_p1 = {tx["id"] for tx in data1["transactions"]}
            ids_p2 = {tx["id"] for tx in data2["transactions"]}

            # Ensure zero intersection between pages
            overlap = ids_p1.intersection(ids_p2)
            self.assertEqual(len(overlap), 0, f"Overlapping transaction IDs across pages: {overlap}")

    async def test_max_limit_enforcement(self):
        """Verify requests requesting more than 15 items per page are rejected with 422."""
        response = await self.client.get("/api/transactions?limit=20")
        self.assertEqual(response.status_code, 422, "API must reject requests with limit > 15")

    async def test_filtered_pagination_total_consistency(self):
        """Verify pagination metadata reflects filtered subset."""
        response = await self.client.get("/api/transactions?type=SUBSIDY&page=1&limit=15")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        pagination = data["pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["limit"], 15)
        self.assertLessEqual(len(data["transactions"]), 15)

        # All returned transactions must match the filter
        for tx in data["transactions"]:
            self.assertEqual(tx["type"], "SUBSIDY")

    async def test_out_of_bounds_page_returns_empty_list(self):
        """Verify requesting a page beyond total_pages returns an empty list gracefully."""
        res = await self.client.get("/api/transactions?page=9999&limit=15")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(len(data["transactions"]), 0)
        self.assertEqual(data["pagination"]["page"], 9999)
        self.assertFalse(data["pagination"]["has_next"])
        self.assertTrue(data["pagination"]["has_prev"])


if __name__ == "__main__":
    unittest.main()
