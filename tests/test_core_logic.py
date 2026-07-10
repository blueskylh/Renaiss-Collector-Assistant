import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "renaiss-collector-assistant" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import renaiss_cli_tools as cli
import bsc_wallet_analyzer as wallet
from common_env import load_dotenv_files


class CoreLogicTests(unittest.TestCase):
    def test_parse_token_id_invalid_is_row_safe(self):
        self.assertIsNone(cli.parse_token_id("not-a-card-url"))
        self.assertEqual(cli.parse_token_id("https://www.renaiss.xyz/card/123456789012345678"), "123456789012345678")

    def test_sequential_duplicate_serials_generate_all_pairs(self):
        rows = [
            {"tokenId": "100A", "serial_number": 100, "serial_raw": "PSA100", "gradingCompany": "PSA", "ask_usdt": 1, "fmv_usd": 2},
            {"tokenId": "100B", "serial_number": 100, "serial_raw": "PSA100", "gradingCompany": "PSA", "ask_usdt": 1, "fmv_usd": 2},
            {"tokenId": "101A", "serial_number": 101, "serial_raw": "PSA101", "gradingCompany": "PSA", "ask_usdt": 1, "fmv_usd": 2},
            {"tokenId": "101B", "serial_number": 101, "serial_raw": "PSA101", "gradingCompany": "PSA", "ask_usdt": 1, "fmv_usd": 2},
        ]
        out = cli.build_sequential_candidates(rows)
        self.assertEqual(len(out), 4)
        self.assertEqual({r["serial_gap"] for r in out}, {1})

    def test_arbitrage_ranks_positive_fmv_when_direct_is_negative(self):
        rows = [
            {"tokenId": "a", "ask_usdt": 100, "top_offer_usdt": 95, "fmv_usd": 150},
            {"tokenId": "b", "ask_usdt": 100, "top_offer_usdt": 110, "fmv_usd": 100},
        ]
        out = cli.build_arbitrage_candidates(rows)
        by_id = {r["tokenId"]: r for r in out}
        self.assertEqual(by_id["a"]["opportunity_type"], "fmv_discount")
        self.assertGreater(by_id["a"]["ranking_value"], 0)
        self.assertEqual(out[0]["tokenId"], "a")

    def test_empty_csv_has_header(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "empty.csv"
            cli.write_csv(p, [], ["a", "b"])
            with p.open(newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        self.assertEqual(rows, [["a", "b"]])

    def test_migration_edges_avoid_usdt_cartesian_false_positive(self):
        old = "0x1111111111111111111111111111111111111111"
        new = "0x2222222222222222222222222222222222222222"
        random_a = "0x3333333333333333333333333333333333333333"
        random_b = "0x4444444444444444444444444444444444444444"
        decoded = {
            "classification": "legacy_wallet_migration",
            "to": wallet.MIGRATION,
            "tx_hash": "0xabc",
            "block_number": 10,
            "renaiss_sbt_batches": [
                {"from": old, "to": wallet.ZERO, "ids": [1, 2], "values": [1, 1]},
                {"from": wallet.ZERO, "to": new, "ids": [1, 2], "values": [1, 1]},
            ],
            "usdt_transfers": [
                {"from": old, "to": new, "amount_usdt": 5},
                {"from": random_a, "to": random_b, "amount_usdt": 9},
            ],
            "renaiss_nft_transfers": [],
            "renaiss_sbt_singles": [],
        }
        edges = wallet.migration_edges(decoded)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["old_wallet"], old)
        self.assertEqual(edges[0]["new_wallet"], new)
        self.assertEqual(edges[0]["migrated_usdt"], 5)

    def test_migration_component_multihop_current_wallet(self):
        a = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        b = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        c = "0xcccccccccccccccccccccccccccccccccccccccc"
        current, cluster, terminals = wallet.migration_component(a, [
            {"old_wallet": a, "new_wallet": b, "block_number": 1},
            {"old_wallet": b, "new_wallet": c, "block_number": 2},
        ])
        self.assertEqual(current, c)
        self.assertEqual(set(cluster), {a, b, c})
        self.assertEqual(terminals, [c])

    def test_metadata_uri_normalization(self):
        self.assertIn("0000000000000000000000000000000000000000000000000000000000000001", wallet.normalize_metadata_uri("https://x/{id}.json", 1))
        self.assertEqual(wallet.normalize_metadata_uri("ipfs://abc/1.json", 1), "https://ipfs.io/ipfs/abc/1.json")

    def test_index_arbitrage_includes_confidence(self):
        old = cli.graded_index_lookup
        try:
            cli.graded_index_lookup = lambda cert, retries=2: {
                "found": True,
                "exact_cert_match": True,
                "normalized_cert": "PSA123",
                "response_cert": "PSA123",
                "data": {"card": {
                    "priceUsdCents": 20000,
                    "confidence": "prime",
                    "lastSaleAt": "2026-07-10T00:00:00.000Z",
                    "href": "/card/test",
                    "name": "Test Card",
                    "gradeLabel": "PSA 10",
                    "company": "PSA",
                }}
            }
            rows, searched, errors = cli.build_index_arbitrage_candidates([
                {"tokenId": "x", "name": "Test Card", "serial_raw": "PSA123", "serial_number": 123, "ask_usdt": 100, "gradingCompany": "PSA", "grade": "10"}
            ], delay=0)
        finally:
            cli.graded_index_lookup = old
        self.assertEqual(searched, 1)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["index_confidence"], "prime")
        self.assertTrue(rows[0]["exact_cert_match"])
        self.assertGreater(rows[0]["index_spread_usdt"], 0)

    def test_jsonl_reader_skips_truncated_last_line(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "data.jsonl"
            p.write_text('{"tokenId":"1"}\n{"tokenId":"2"', encoding="utf-8")
            rows = cli.read_jsonl(p)
        self.assertEqual(rows, [{"tokenId": "1"}])

    def test_sequential_requires_psa_by_default(self):
        rows = [
            {"tokenId": "1", "serial_number": 100, "serial_raw": "BGS100", "gradingCompany": "BGS", "ask_usdt": 1},
            {"tokenId": "2", "serial_number": 101, "serial_raw": "PSA101", "gradingCompany": "PSA", "ask_usdt": 1},
        ]
        self.assertEqual(cli.build_sequential_candidates(rows), [])

    def test_expired_ask_skipped_in_arbitrage(self):
        rows = [{"tokenId": "expired", "ask_usdt": 1, "top_offer_usdt": 100, "askExpiresAt": "2000-01-01T00:00:00Z"}]
        self.assertEqual(cli.build_arbitrage_candidates(rows), [])

    def test_multi_user_sbt_overlap_without_direct_transfer_is_not_edge(self):
        old_a = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        old_b = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        new_c = "0xcccccccccccccccccccccccccccccccccccccccc"
        new_d = "0xdddddddddddddddddddddddddddddddddddddddd"
        decoded = {
            "classification": "legacy_wallet_migration",
            "to": wallet.MIGRATION,
            "tx_hash": "0xmulti",
            "block_number": 1,
            "renaiss_sbt_batches": [
                {"from": old_a, "to": wallet.ZERO, "ids": [5]},
                {"from": old_b, "to": wallet.ZERO, "ids": [5]},
                {"from": wallet.ZERO, "to": new_c, "ids": [5]},
                {"from": wallet.ZERO, "to": new_d, "ids": [5]},
            ],
            "usdt_transfers": [],
            "renaiss_nft_transfers": [],
            "renaiss_sbt_singles": [],
        }
        self.assertEqual(wallet.migration_edges(decoded), [])

    def test_dotenv_loader(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".env"
            p.write_text('RENAISS_UNIT_TEST="ok"\n', encoding="utf-8")
            load_dotenv_files([p], override=True)
            self.assertEqual(os.getenv("RENAISS_UNIT_TEST"), "ok")


if __name__ == "__main__":
    unittest.main()
