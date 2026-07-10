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
            {"tokenId": "100A", "serial_number": 100, "serial_raw": "PSA100", "ask_usdt": 1, "fmv_usd": 2},
            {"tokenId": "100B", "serial_number": 100, "serial_raw": "PSA100", "ask_usdt": 1, "fmv_usd": 2},
            {"tokenId": "101A", "serial_number": 101, "serial_raw": "PSA101", "ask_usdt": 1, "fmv_usd": 2},
            {"tokenId": "101B", "serial_number": 101, "serial_raw": "PSA101", "ask_usdt": 1, "fmv_usd": 2},
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
        old = cli.search_index_by_serial
        try:
            cli.search_index_by_serial = lambda serial, limit=3: {
                "data": {"results": [{
                    "priceUsdCents": 20000,
                    "confidence": "prime",
                    "lastSaleAt": "2026-07-10T00:00:00.000Z",
                    "href": "/card/test",
                    "name": "Test Card",
                    "gradeLabel": "PSA 10",
                    "company": "PSA",
                }]}
            }
            rows, searched = cli.build_index_arbitrage_candidates([
                {"tokenId": "x", "name": "Test Card", "serial_raw": "PSA123", "serial_number": 123, "ask_usdt": 100, "gradingCompany": "PSA", "grade": "10"}
            ], delay=0)
        finally:
            cli.search_index_by_serial = old
        self.assertEqual(searched, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["index_confidence"], "prime")
        self.assertGreater(rows[0]["index_spread_usdt"], 0)

    def test_dotenv_loader(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".env"
            p.write_text('RENAISS_UNIT_TEST="ok"\n', encoding="utf-8")
            load_dotenv_files([p], override=True)
            self.assertEqual(os.getenv("RENAISS_UNIT_TEST"), "ok")


if __name__ == "__main__":
    unittest.main()
