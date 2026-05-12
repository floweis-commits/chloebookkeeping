"""
Reconciliation Engine

Matches transactions across sources (QuickBooks, Shopify, PayPal, Stripe)
to identify discrepancies, duplicates, and unmatched items.

Reconciliation rules:
- A transaction is "matched" when the same amount appears in QuickBooks
  AND at least one payment processor within a ±3-day window.
- Unmatched processor transactions → potential missing QB entries.
- Unmatched QB transactions → potential unrecorded payments.
- Amount mismatches (QB vs processor differ by >$0.01) → flagged for review.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class ReconciliationMatch:
    qb_transaction: dict[str, Any] | None
    processor_transaction: dict[str, Any]
    processor_source: str  # "shopify" | "paypal" | "stripe"
    match_type: str        # "matched" | "unmatched_processor" | "unmatched_qb" | "amount_mismatch"
    delta: float = 0.0     # QB amount - processor amount (non-zero for mismatches)


@dataclass
class ReconciliationResult:
    period_start: str
    period_end: str
    matched: list[ReconciliationMatch] = field(default_factory=list)
    unmatched_processor: list[ReconciliationMatch] = field(default_factory=list)
    unmatched_qb: list[dict[str, Any]] = field(default_factory=list)
    amount_mismatches: list[ReconciliationMatch] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, Any]:
        total_processor = len(self.matched) + len(self.unmatched_processor) + len(self.amount_mismatches)
        return {
            "total_processor_transactions": total_processor,
            "matched": len(self.matched),
            "unmatched_processor": len(self.unmatched_processor),
            "unmatched_qb": len(self.unmatched_qb),
            "amount_mismatches": len(self.amount_mismatches),
            "match_rate": len(self.matched) / total_processor if total_processor else 1.0,
            "needs_review": len(self.unmatched_processor) + len(self.unmatched_qb) + len(self.amount_mismatches),
        }


class ReconcilerAgent:
    MATCH_WINDOW_DAYS = 3
    AMOUNT_TOLERANCE = 0.02  # 2 cents — covers rounding differences

    def reconcile(
        self,
        qb_transactions: list[dict[str, Any]],
        processor_transactions: list[dict[str, Any]],
        processor_source: str,
        period_start: str,
        period_end: str,
    ) -> ReconciliationResult:
        """
        Reconcile QuickBooks transactions against a single processor source.

        Args:
            qb_transactions: List from QB with at minimum {id, date, amount, description}
            processor_transactions: List from Shopify/PayPal/Stripe with same shape
            processor_source: "shopify" | "paypal" | "stripe"
            period_start: "YYYY-MM-DD"
            period_end: "YYYY-MM-DD"
        """
        result = ReconciliationResult(period_start=period_start, period_end=period_end)
        unmatched_qb = list(qb_transactions)  # will remove matched ones

        for proc_txn in processor_transactions:
            proc_amount = abs(float(proc_txn.get("amount", 0)))
            proc_date = self._parse_date(proc_txn.get("date", ""))
            if proc_date is None:
                continue

            best_match: dict[str, Any] | None = None
            for qb_txn in unmatched_qb:
                qb_amount = abs(float(qb_txn.get("amount", 0)))
                qb_date = self._parse_date(qb_txn.get("date", ""))
                if qb_date is None:
                    continue

                date_diff = abs((qb_date - proc_date).days)
                amount_diff = abs(qb_amount - proc_amount)

                if date_diff <= self.MATCH_WINDOW_DAYS and amount_diff <= self.AMOUNT_TOLERANCE:
                    best_match = qb_txn
                    break  # First match wins; good enough for bookkeeping

            if best_match is not None:
                delta = float(best_match.get("amount", 0)) - float(proc_txn.get("amount", 0))
                if abs(delta) > self.AMOUNT_TOLERANCE:
                    result.amount_mismatches.append(ReconciliationMatch(
                        qb_transaction=best_match,
                        processor_transaction=proc_txn,
                        processor_source=processor_source,
                        match_type="amount_mismatch",
                        delta=round(delta, 2),
                    ))
                else:
                    result.matched.append(ReconciliationMatch(
                        qb_transaction=best_match,
                        processor_transaction=proc_txn,
                        processor_source=processor_source,
                        match_type="matched",
                    ))
                unmatched_qb.remove(best_match)
            else:
                result.unmatched_processor.append(ReconciliationMatch(
                    qb_transaction=None,
                    processor_transaction=proc_txn,
                    processor_source=processor_source,
                    match_type="unmatched_processor",
                ))

        result.unmatched_qb = unmatched_qb
        return result

    def reconcile_all_sources(
        self,
        qb_transactions: list[dict[str, Any]],
        shopify_transactions: list[dict[str, Any]] | None,
        paypal_transactions: list[dict[str, Any]] | None,
        stripe_transactions: list[dict[str, Any]] | None,
        period_start: str,
        period_end: str,
    ) -> dict[str, ReconciliationResult]:
        """
        Run reconciliation against each connected processor separately.
        Returns a dict keyed by processor source name.
        """
        results: dict[str, ReconciliationResult] = {}

        if shopify_transactions:
            results["shopify"] = self.reconcile(
                qb_transactions, shopify_transactions, "shopify", period_start, period_end
            )
        if paypal_transactions:
            results["paypal"] = self.reconcile(
                qb_transactions, paypal_transactions, "paypal", period_start, period_end
            )
        if stripe_transactions:
            results["stripe"] = self.reconcile(
                qb_transactions, stripe_transactions, "stripe", period_start, period_end
            )

        return results

    def to_flagged_items(
        self, results: dict[str, ReconciliationResult]
    ) -> list[dict[str, Any]]:
        """
        Convert reconciliation discrepancies into FlaggedItem dicts for the DB.
        """
        flagged = []
        for source, result in results.items():
            for match in result.unmatched_processor:
                proc = match.processor_transaction
                flagged.append({
                    "source": source,
                    "type": "unmatched_processor",
                    "description": (
                        f"${abs(float(proc.get('amount', 0))):,.2f} on {proc.get('date', '?')} "
                        f"from {source} — no matching QB entry found"
                    ),
                    "amount": abs(float(proc.get("amount", 0))),
                    "transaction_id": proc.get("id"),
                    "raw": proc,
                })
            for match in result.amount_mismatches:
                proc = match.processor_transaction
                flagged.append({
                    "source": source,
                    "type": "amount_mismatch",
                    "description": (
                        f"Amount mismatch of ${abs(match.delta):,.2f} between QB and {source} "
                        f"on {proc.get('date', '?')}"
                    ),
                    "amount": match.delta,
                    "transaction_id": proc.get("id"),
                    "raw": {"processor": proc, "qb": match.qb_transaction},
                })
            for qb_txn in result.unmatched_qb:
                flagged.append({
                    "source": "quickbooks",
                    "type": "unmatched_qb",
                    "description": (
                        f"${abs(float(qb_txn.get('amount', 0))):,.2f} QB entry on "
                        f"{qb_txn.get('date', '?')} — no matching {source} transaction found"
                    ),
                    "amount": abs(float(qb_txn.get("amount", 0))),
                    "transaction_id": qb_txn.get("id"),
                    "raw": qb_txn,
                })
        return flagged

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
            try:
                return datetime.strptime(date_str[:10], "%Y-%m-%d")
            except ValueError:
                pass
        return None
