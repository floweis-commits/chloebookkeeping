"""
Insights Agent — surfaces anomalies, trends, and tax tips via GLM.
"""

from typing import Any

from openai import AsyncOpenAI

from backend.config import settings


class InsightsAgent:
    def __init__(self):
        self.glm = AsyncOpenAI(
            api_key=settings.glm_api_key,
            base_url=settings.glm_base_url,
        )

    async def generate(
        self,
        current_pl: dict[str, float],
        prior_pl: dict[str, float],
        balance_sheet: dict[str, float],
        period_label: str,
    ) -> dict[str, Any]:
        """
        Compare current vs prior period financials and return structured insights.

        Returns:
            {
                "tax_tips": [...],
                "anomalies": [...],
                "summary": "...",
            }
        """
        lines = [f"Period: {period_label}", ""]
        lines.append("Current period P&L:")
        for k, v in sorted(current_pl.items(), key=lambda x: abs(x[1]), reverse=True)[:15]:
            lines.append(f"  {k}: ${v:,.2f}")

        lines.append("\nPrior period P&L:")
        for k, v in sorted(prior_pl.items(), key=lambda x: abs(x[1]), reverse=True)[:15]:
            lines.append(f"  {k}: ${v:,.2f}")

        lines.append("\nBalance sheet (key accounts):")
        for k, v in balance_sheet.items():
            lines.append(f"  {k}: ${v:,.2f}")

        prompt = "\n".join(lines)

        response = await self.glm.chat.completions.create(
            model=settings.glm_model,
            max_tokens=500,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a CPA reviewing monthly financials. Return a JSON object with three keys:\n"
                        '- "tax_tips": array of 2-3 actionable strings referencing specific accounts/amounts\n'
                        '- "anomalies": array of 1-2 strings describing unusual changes vs prior period\n'
                        '- "summary": one sentence executive summary\n'
                        "Be specific and concise. Numbers should be dollar-formatted."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        import json
        raw = response.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"tax_tips": [], "anomalies": [], "summary": raw}
