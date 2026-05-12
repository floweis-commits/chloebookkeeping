"""
Transaction Categorizer Agent

Accepts a batch of raw transactions, maps them to Chloe's chart of accounts
using rule-based matching first, then GLM for ambiguous ones.
Flags low-confidence items for human review.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from backend.config import settings

# ── Chart of accounts ─────────────────────────────────────────────────
# Maps canonical category name → list of keyword patterns to match against
# transaction description/memo (case-insensitive).
CHART_OF_ACCOUNTS: dict[str, list[str]] = {
    # Income
    "PayPal Sales": ["paypal"],
    "Sales": ["sale", "revenue", "shopify payout", "stripe payout"],
    "Sales of Product Income": ["product", "merchandise", "inventory sale"],
    # Expenses
    "Car & Truck - Fuel": ["fuel", "gasoline", "gas station", "chevron", "shell", "exxon", "bp"],
    "Contractors": ["contractor", "freelance", "subcontractor", "1099"],
    "Employee Expense Reimbursements": ["reimbursement", "expense report"],
    "Horse Expenses": ["horse", "equine", "farrier", "hay", "feed", "saddle", "tack"],
    "Insurance": ["insurance", "geico", "state farm", "allstate", "progressive"],
    "Legal & Professional Services": ["attorney", "lawyer", "cpa", "accountant", "legal", "notary"],
    "Meals": ["restaurant", "doordash", "grubhub", "ubereats", "coffee", "lunch", "dinner"],
    "Office Supplies & Software": ["amazon", "staples", "office depot", "software", "subscription", "saas", "zoom", "slack", "adobe"],
    "Pasture Expenses": ["pasture", "fence", "hay field", "grazing", "lease"],
    "Payment Processing Fees": ["paypal fee", "stripe fee", "shopify fee", "processing fee", "transaction fee"],
    "Payroll Expenses - Officer Wages": ["officer wage", "owner salary", "draw"],
    "Payroll Expenses - Payroll Fees": ["payroll fee", "gusto", "adp", "paychex"],
    "Payroll Expenses - Taxes": ["payroll tax", "fica", "futa", "suta", "employer tax"],
    "Postage & Shipping": ["usps", "fedex", "ups", "shipping", "postage", "stamps"],
    "Retreat Expenses": ["retreat", "workshop venue", "event space"],
    "Sales Tax": ["sales tax", "tax collected"],
    "Travel": ["airline", "hotel", "airbnb", "uber", "lyft", "flight", "lodging", "delta", "southwest", "united"],
    "Vet Expenses": ["veterinar", "vet clinic", "animal hospital", "pet med"],
}

INCOME_CATEGORIES = {"PayPal Sales", "Sales", "Sales of Product Income"}


@dataclass
class CategorizedTransaction:
    transaction_id: str
    original: dict[str, Any]
    category: str
    confidence: float  # 0.0–1.0
    method: str        # "rule" | "ai" | "manual"
    flagged: bool = False
    flag_reason: str = ""


def _rule_match(description: str) -> tuple[str | None, float]:
    """Return (category, confidence) if a keyword rule matches, else (None, 0)."""
    desc = description.lower()
    for category, keywords in CHART_OF_ACCOUNTS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", desc) or kw in desc:
                return category, 0.95
    return None, 0.0


class CategorizerAgent:
    CONFIDENCE_THRESHOLD = 0.70

    def __init__(self):
        self.glm = AsyncOpenAI(
            api_key=settings.glm_api_key,
            base_url=settings.glm_base_url,
        )

    async def categorize_batch(
        self, transactions: list[dict[str, Any]]
    ) -> list[CategorizedTransaction]:
        """
        Categorize a list of transactions.

        Each transaction dict must have at minimum:
            - id: str
            - description: str
            - amount: float (positive = income, negative = expense)
            - date: str
        """
        results: list[CategorizedTransaction] = []
        needs_ai: list[dict[str, Any]] = []

        # Pass 1: rule-based
        for txn in transactions:
            desc = txn.get("description", "") or txn.get("memo", "")
            category, confidence = _rule_match(desc)
            if category:
                results.append(CategorizedTransaction(
                    transaction_id=txn["id"],
                    original=txn,
                    category=category,
                    confidence=confidence,
                    method="rule",
                ))
            else:
                needs_ai.append(txn)

        # Pass 2: AI for ambiguous transactions
        if needs_ai:
            ai_results = await self._ai_categorize(needs_ai)
            results.extend(ai_results)

        # Flag low-confidence
        for r in results:
            if r.confidence < self.CONFIDENCE_THRESHOLD:
                r.flagged = True
                r.flag_reason = f"Low confidence ({r.confidence:.0%}) — needs bookkeeper review"

        return results

    async def _ai_categorize(
        self, transactions: list[dict[str, Any]]
    ) -> list[CategorizedTransaction]:
        categories_list = "\n".join(f"- {c}" for c in CHART_OF_ACCOUNTS)
        txn_lines = "\n".join(
            f"{i+1}. id={t['id']} desc=\"{t.get('description', '')}\" amount={t.get('amount', 0)}"
            for i, t in enumerate(transactions)
        )

        response = await self.glm.chat.completions.create(
            model=settings.glm_model,
            max_tokens=800,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a CPA categorizing business transactions. "
                        "Return a JSON array where each element has: "
                        '{"id": "<transaction_id>", "category": "<exact category name from list>", "confidence": <0.0-1.0>}. '
                        "Only use categories from this list:\n" + categories_list
                    ),
                },
                {
                    "role": "user",
                    "content": f"Categorize these transactions:\n{txn_lines}",
                },
            ],
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or '{"results":[]}'
        try:
            parsed = json.loads(raw)
            # GLM may return {"results": [...]} or just [...]
            items = parsed if isinstance(parsed, list) else parsed.get("results", list(parsed.values())[0] if parsed else [])
        except (json.JSONDecodeError, IndexError):
            items = []

        id_map = {t["id"]: t for t in transactions}
        ai_results: list[CategorizedTransaction] = []

        categorized_ids = {item.get("id") for item in items}
        for item in items:
            txn_id = item.get("id", "")
            txn = id_map.get(txn_id, {})
            ai_results.append(CategorizedTransaction(
                transaction_id=txn_id,
                original=txn,
                category=item.get("category", "Uncategorized"),
                confidence=float(item.get("confidence", 0.5)),
                method="ai",
            ))

        # Any transactions GLM didn't return get flagged as uncategorized
        for txn in transactions:
            if txn["id"] not in categorized_ids:
                ai_results.append(CategorizedTransaction(
                    transaction_id=txn["id"],
                    original=txn,
                    category="Uncategorized",
                    confidence=0.0,
                    method="ai",
                    flagged=True,
                    flag_reason="AI could not determine category",
                ))

        return ai_results
