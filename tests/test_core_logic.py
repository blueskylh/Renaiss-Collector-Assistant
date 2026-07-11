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
            rows, searched, errors, states = cli.build_index_arbitrage_candidates([
                {"tokenId": "x", "name": "Test Card", "serial_raw": "PSA123", "serial_number": 123, "ask_usdt": 100, "gradingCompany": "PSA", "grade": "10"}
            ], delay=0)
        finally:
            cli.graded_index_lookup = old
        self.assertEqual(searched, 1)
        self.assertEqual(errors, [])
        self.assertEqual(len(states), 1)
        self.assertEqual(states[0]["status"], "candidate")
        self.assertTrue(states[0]["terminal"])
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

    def test_graded_lookup_found_fallback_without_found_field(self):
        old = cli.renaiss_index_get
        try:
            cli.renaiss_index_get = lambda path, retries=2: {
                "data": {"cert": "PSA12345", "card": {"priceUsdCents": 12345}}
            }
            lookup = cli.graded_index_lookup("PSA12345")
        finally:
            cli.renaiss_index_get = old
        self.assertTrue(lookup["found"])
        self.assertTrue(lookup["exact_cert_match"])

    def test_graded_lookup_falls_back_to_card_overview_price(self):
        old = cli.renaiss_index_get
        try:
            def fake_get(path, retries=2):
                if path.startswith("/v1/graded/"):
                    return {"data": {
                        "cert": "PSA97970920",
                        "found": True,
                        "card": {
                            "priceUsdCents": None,
                            "href": "/card/pokemon/test-set/002-vaporeon-vmax-psa-9-japanese-e234b3d8",
                            "name": "Vaporeon Vmax",
                        },
                    }}
                if path == "/v1/cards/pokemon/test-set/002-vaporeon-vmax-psa-9-japanese-e234b3d8":
                    return {"data": {"priceUsdCents": 1693, "confidence": "low", "sourceCount": 1, "observationCount": 5}}
                raise AssertionError(path)
            cli.renaiss_index_get = fake_get
            lookup = cli.graded_index_lookup("PSA97970920")
            best = cli.graded_price_candidate({"tokenId": "x"}, lookup)
        finally:
            cli.renaiss_index_get = old
        self.assertTrue(lookup["found"])
        self.assertEqual(best["priceUsdCents"], 1693)
        self.assertEqual(best["confidence"], "low")
        self.assertEqual(lookup["data"]["overview"]["observationCount"], 5)

    def test_marketplace_normalization_preserves_expiry_for_index_scan(self):
        card = {
            "tokenId": "1",
            "askPriceInUSDT": "1000000000000000000",
            "fmvPriceInUSD": "100",
            "askExpiresAt": "2000-01-01T00:00:00Z",
            "attributes": [{"trait": "Serial", "value": "PSA123"}],
            "gradingCompany": "PSA",
        }
        row = cli.normalize_market_card(card, "2026-01-01 00:00:00 UTC")
        self.assertEqual(row["askExpiresAt"], "2000-01-01T00:00:00Z")
        self.assertTrue(row["ask_is_expired_at_collection"])
        old = cli.graded_index_lookup
        try:
            cli.graded_index_lookup = lambda cert, retries=2: (_ for _ in ()).throw(AssertionError("expired rows should not call index"))
            rows, searched, errors, states = cli.build_index_arbitrage_candidates([row], delay=0)
        finally:
            cli.graded_index_lookup = old
        self.assertEqual(rows, [])
        self.assertEqual(searched, 0)
        self.assertEqual(errors[0]["error"], "expired_ask_skipped")
        self.assertEqual(states[0]["status"], "expired")

    def test_index_resume_state_skips_terminal_non_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "state.jsonl"
            p.write_text(json.dumps({"tokenId": "x", "serial": "PSA123", "terminal": True}) + "\n", encoding="utf-8")
            self.assertEqual(cli.read_terminal_state_keys(p), {("x", "PSA123")})

    def test_wallet_summary_filters_unrelated_batch_migrations(self):
        a = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        b = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        c = "0xcccccccccccccccccccccccccccccccccccccccc"
        d = "0xdddddddddddddddddddddddddddddddddddddddd"
        decoded = {
            "classification": "legacy_wallet_migration",
            "to": wallet.MIGRATION,
            "tx_hash": "0xbatch",
            "block_number": 1,
            "usdt_transfers": [
                {"from": a, "to": b, "amount_usdt": 1},
                {"from": c, "to": d, "amount_usdt": 1},
            ],
            "renaiss_nft_transfers": [],
            "renaiss_sbt_batches": [
                {"from": a, "to": wallet.ZERO, "ids": [1]},
                {"from": wallet.ZERO, "to": b, "ids": [1]},
                {"from": c, "to": wallet.ZERO, "ids": [2]},
                {"from": wallet.ZERO, "to": d, "ids": [2]},
            ],
            "renaiss_sbt_singles": [],
            "log_contract_counts": {},
        }
        summary = wallet.summarize_cluster(a, {}, {"0xbatch": decoded}, {})
        self.assertEqual(set(summary["wallet_cluster"]), {a, b})
        self.assertEqual(len(summary["migrations"]), 1)
        self.assertEqual(summary["migrations"][0]["old_wallet"], a)
        self.assertEqual(summary["migrations"][0]["new_wallet"], b)

    def test_wallet_pnl_completeness_partial_for_history_and_decode_errors(self):
        a = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        old_fetch_history = wallet.fetch_wallet_history
        old_fetch_detail = wallet.fetch_wallet_detail
        old_decode_tx = wallet.decode_tx
        try:
            wallet.fetch_wallet_history = lambda address, limit=100, source="auto", max_pages=5: {
                "data": [{"tx_hash": "0xdead"}],
                "meta": {"has_more_last": True},
                "error": None,
            }
            wallet.fetch_wallet_detail = lambda address, source="auto": {"data": {}, "meta": {}, "source": "test"}
            wallet.decode_tx = lambda h: (_ for _ in ()).throw(RuntimeError("decode failed"))
            report = wallet.build_wallet_report(a, max_wallets=20)
        finally:
            wallet.fetch_wallet_history = old_fetch_history
            wallet.fetch_wallet_detail = old_fetch_detail
            wallet.decode_tx = old_decode_tx
        summary = report["summary"]
        self.assertEqual(summary["pnl_completeness"], "partial")
        self.assertTrue(summary["history_scan_truncated"])
        self.assertEqual(summary["decode_error_count"], 1)

    def test_dotenv_loader(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / ".env"
            p.write_text('RENAISS_UNIT_TEST="ok"\n', encoding="utf-8")
            load_dotenv_files([p], override=True)
            self.assertEqual(os.getenv("RENAISS_UNIT_TEST"), "ok")

    def test_alchemy_bnb_rpc_url_derives_from_key(self):
        old_key = os.environ.get("ALCHEMY_API_KEY")
        old_url = os.environ.get("ALCHEMY_BNB_RPC_URL")
        try:
            os.environ["ALCHEMY_API_KEY"] = "unit_test_key"
            os.environ.pop("ALCHEMY_BNB_RPC_URL", None)
            self.assertEqual(wallet.alchemy_bnb_rpc_url(), "https://bnb-mainnet.g.alchemy.com/v2/unit_test_key")
        finally:
            if old_key is None:
                os.environ.pop("ALCHEMY_API_KEY", None)
            else:
                os.environ["ALCHEMY_API_KEY"] = old_key
            if old_url is None:
                os.environ.pop("ALCHEMY_BNB_RPC_URL", None)
            else:
                os.environ["ALCHEMY_BNB_RPC_URL"] = old_url

    def test_alchemy_transfer_merge_dedupes_hash(self):
        rows = {}
        wallet._merge_history_row(rows, {
            "hash": "0xabc",
            "blockNum": "0x10",
            "from": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "to": "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "category": "erc20",
            "asset": "USDT",
            "metadata": {"blockTimestamp": "2026-07-10T00:00:00Z"},
        })
        wallet._merge_history_row(rows, {
            "hash": "0xabc",
            "blockNum": "0x10",
            "from": "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "to": "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
            "category": "erc721",
            "asset": "NFT",
            "metadata": {"blockTimestamp": "2026-07-10T00:00:00Z"},
        })
        self.assertEqual(list(rows), ["0xabc"])
        self.assertEqual(rows["0xabc"]["block_number"], 16)
        self.assertEqual(rows["0xabc"]["timestamp"], 1783641600)
        self.assertEqual(set(rows["0xabc"]["alchemy_categories"]), {"erc20", "erc721"})
        self.assertEqual(set(rows["0xabc"]["alchemy_assets"]), {"USDT", "NFT"})

    def test_card_details_resume_limit_filters_before_limit(self):
        token_ids = [str(i) for i in range(1, 21)]
        pending = cli.build_pending_token_ids(token_ids, completed={str(i) for i in range(1, 11)}, resume=True, retry_errors=True, limit=5)
        self.assertEqual(pending, ["11", "12", "13", "14", "15"])
        self.assertEqual("cli" if len(pending) <= 10 else "api", "cli")

    def test_index_resume_max_cards_filters_skip_before_limit(self):
        old = cli.graded_index_lookup
        seen = []
        try:
            def fake_lookup(cert, retries=2):
                seen.append(cert)
                return {
                    "found": True,
                    "exact_cert_match": True,
                    "normalized_cert": cert,
                    "response_cert": cert,
                    "data": {"card": {"priceUsdCents": 20000, "confidence": "prime"}},
                }
            cli.graded_index_lookup = fake_lookup
            rows = [
                {"tokenId": str(i), "name": f"Card {i}", "serial_raw": f"PSA{i}", "serial_number": i, "ask_usdt": 100}
                for i in range(1, 6)
            ]
            out, searched, errors, states = cli.build_index_arbitrage_candidates(
                rows,
                max_cards=2,
                skip_keys={("1", "PSA1"), ("2", "PSA2")},
                delay=0,
            )
        finally:
            cli.graded_index_lookup = old
        self.assertEqual(seen, ["PSA3", "PSA4"])
        self.assertEqual(searched, 2)
        self.assertEqual(len(out), 2)
        self.assertEqual(len(states), 2)
        self.assertEqual(errors, [])

    def test_index_terminal_state_is_snapshot_scoped_and_expires(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "state.jsonl"
            p.write_text(
                json.dumps({"tokenId": "x", "serial": "PSA123", "terminal": True, "snapshot_id": "A", "expires_at_utc": "2099-01-01 00:00:00 UTC"}) + "\n" +
                json.dumps({"tokenId": "y", "serial": "PSA124", "terminal": True, "snapshot_id": "A", "expires_at_utc": "2000-01-01 00:00:00 UTC"}) + "\n" +
                json.dumps({"tokenId": "z", "serial": "PSA125", "terminal": True, "snapshot_id": "B", "expires_at_utc": "2099-01-01 00:00:00 UTC"}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(cli.read_terminal_state_keys(p, snapshot_id="A"), {("x", "PSA123")})

    def test_unknown_ask_expiry_is_not_treated_as_active(self):
        self.assertEqual(cli.ask_expiry_status("not-a-date"), "unknown")
        self.assertEqual(cli.build_arbitrage_candidates([{"tokenId": "bad", "ask_usdt": 1, "top_offer_usdt": 10, "askExpiresAt": "not-a-date"}]), [])
        old = cli.graded_index_lookup
        try:
            cli.graded_index_lookup = lambda cert, retries=2: (_ for _ in ()).throw(AssertionError("unknown expiry should not call index"))
            rows, searched, errors, states = cli.build_index_arbitrage_candidates([
                {"tokenId": "bad", "serial_raw": "PSA123", "serial_number": 123, "ask_usdt": 1, "askExpiresAt": "not-a-date"}
            ], delay=0)
        finally:
            cli.graded_index_lookup = old
        self.assertEqual(rows, [])
        self.assertEqual(searched, 0)
        self.assertEqual(errors[0]["error"], "unknown_ask_expiry_skipped")
        self.assertEqual(states[0]["status"], "unknown_ask_expiry")

    def test_jsonl_reader_raises_on_complete_bad_last_line(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.jsonl"
            p.write_text('{"tokenId":"1"}\n{"tokenId":"2"\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                cli.read_jsonl(p)

    def test_wallet_report_history_failure_becomes_partial(self):
        a = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        old_fetch_history = wallet.fetch_wallet_history
        old_fetch_detail = wallet.fetch_wallet_detail
        try:
            wallet.fetch_wallet_history = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("history down"))
            wallet.fetch_wallet_detail = lambda address, source="auto": {"data": {}, "meta": {}, "source": "test"}
            report = wallet.build_wallet_report(a, max_wallets=20)
        finally:
            wallet.fetch_wallet_history = old_fetch_history
            wallet.fetch_wallet_detail = old_fetch_detail
        summary = report["summary"]
        self.assertEqual(summary["pnl_completeness"], "partial")
        self.assertTrue(summary["history_scan_truncated"])
        self.assertIn(a, summary["history_errors"])

    def test_pack_purchase_infers_batch_multiples(self):
        catalog = [{"slug": "omega", "price_usdt": 48.0}, {"slug": "champion-pack", "price_usdt": 100.0}]
        five = wallet.infer_pack_purchase(240.0, catalog)
        ten = wallet.infer_pack_purchase(480.0, catalog)
        self.assertEqual(five["pack_type"], "omega")
        self.assertEqual(five["pack_count"], 5)
        self.assertEqual(ten["pack_count"], 10)

    def test_renaiss_custom_sbt_single_topic_prefix_decodes(self):
        self.assertTrue(wallet.is_sbt_transfer_single_topic("0xc3d58168" + "0" * 56))
        sid, val = wallet.decode_transfer_single("0x" + f"{199:064x}" + f"{1:064x}")
        self.assertEqual((sid, val), (199, 1))

    def test_sbt_transfer_balance_delta_for_owner(self):
        owner = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        transfer = {"from": wallet.ZERO, "to": owner, "erc1155Metadata": [{"tokenId": "0xc7", "value": "0x01"}]}
        self.assertEqual(wallet.sbt_transfer_balance_delta_for_owner(owner, transfer)[199], 1)
        transfer_out = {"from": owner, "to": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "erc1155Metadata": [{"tokenId": "0xc7", "value": "0x01"}]}
        self.assertEqual(wallet.sbt_transfer_balance_delta_for_owner(owner, transfer_out)[199], -1)


if __name__ == "__main__":
    unittest.main()
