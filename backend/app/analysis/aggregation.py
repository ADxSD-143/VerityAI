"""Conservative, transparent evidence aggregation.

Rules are explicit and threshold-based rather than an opaque weighted formula. A
passage counts as a strong supporter/contradictor when its NLI argmax label is
entailment/contradiction *and* the score is at or above ``tau``.

Policy (documented, and deliberately not tuned on the evaluation sample):
  * no strong evidence of either kind -> INSUFFICIENT_EVIDENCE;
  * strong support and strong contradiction -> CONFLICTING_EVIDENCE;
  * otherwise the side with strong evidence decides, and ``limited_corroboration``
    is set when that side rests on fewer than two independent sources.

A verdict that rests on a **single independent source** must clear a higher bar
(``tau_single``) than a corroborated one. A lone passage whose best score sits between
``tau`` and ``tau_single`` is too weak to carry a verdict on its own and yields
INSUFFICIENT_EVIDENCE instead of SUPPORTED/REFUTED. This closes the failure mode where one
spurious entailment carried a nonsense claim.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..schemas.models import Verdict


@dataclass
class AggregateInput:
    label: str
    score: float
    group: int


@dataclass
class AggregateResult:
    status: Verdict
    explanation: str
    limited_corroboration: bool
    support_passages: int
    contradict_passages: int
    support_sources: int
    contradict_sources: int
    independent_groups: int


def aggregate(
    items: list[AggregateInput], *, tau: float, tau_single: float = 0.75
) -> AggregateResult:
    strong = [item for item in items if item.score >= tau]
    support = [item for item in strong if item.label == "entailment"]
    contradict = [item for item in strong if item.label == "contradiction"]

    s_pass, c_pass = len(support), len(contradict)
    s_src = len({item.group for item in support})
    c_src = len({item.group for item in contradict})
    groups = len({item.group for item in items})

    if not items:
        return AggregateResult(
            status=Verdict.INSUFFICIENT_EVIDENCE,
            explanation="No evidence passages were retrieved for this claim.",
            limited_corroboration=False,
            support_passages=0, contradict_passages=0,
            support_sources=0, contradict_sources=0, independent_groups=0,
        )

    if s_pass == 0 and c_pass == 0:
        return AggregateResult(
            status=Verdict.INSUFFICIENT_EVIDENCE,
            explanation=(
                f"{len(items)} passage(s) were retrieved but none entailed or "
                f"contradicted the claim at NLI score >= {tau:.2f}."
            ),
            limited_corroboration=False,
            support_passages=0, contradict_passages=0,
            support_sources=0, contradict_sources=0, independent_groups=groups,
        )

    if s_pass > 0 and c_pass > 0:
        return AggregateResult(
            status=Verdict.CONFLICTING_EVIDENCE,
            explanation=(
                f"{s_pass} passage(s) from {s_src} independent source(s) support the "
                f"claim while {c_pass} passage(s) from {c_src} independent source(s) "
                f"contradict it. The evidence is in conflict; no verdict is forced."
            ),
            limited_corroboration=False,
            support_passages=s_pass, contradict_passages=c_pass,
            support_sources=s_src, contradict_sources=c_src, independent_groups=groups,
        )

    if s_pass > 0:
        if s_src < 2 and max(item.score for item in support) < tau_single:
            return AggregateResult(
                status=Verdict.INSUFFICIENT_EVIDENCE,
                explanation=(
                    f"{s_pass} passage(s) from a single independent source entail the "
                    f"claim, but the best NLI score is below the {tau_single:.2f} required "
                    f"to stand on a single source; no verdict is given."
                ),
                limited_corroboration=False,
                support_passages=s_pass, contradict_passages=0,
                support_sources=s_src, contradict_sources=0, independent_groups=groups,
            )
        limited = s_src < 2
        return AggregateResult(
            status=Verdict.SUPPORTED,
            explanation=(
                f"{s_pass} passage(s) from {s_src} independent source(s) entail the "
                f"claim (NLI score >= {tau:.2f}); no strong contradicting evidence was "
                f"retrieved."
                + (" Corroboration is limited to a single source." if limited else "")
            ),
            limited_corroboration=limited,
            support_passages=s_pass, contradict_passages=0,
            support_sources=s_src, contradict_sources=0, independent_groups=groups,
        )

    if c_src < 2 and max(item.score for item in contradict) < tau_single:
        return AggregateResult(
            status=Verdict.INSUFFICIENT_EVIDENCE,
            explanation=(
                f"{c_pass} passage(s) from a single independent source contradict the "
                f"claim, but the best NLI score is below the {tau_single:.2f} required "
                f"to stand on a single source; no verdict is given."
            ),
            limited_corroboration=False,
            support_passages=0, contradict_passages=c_pass,
            support_sources=0, contradict_sources=c_src, independent_groups=groups,
        )
    limited = c_src < 2
    return AggregateResult(
        status=Verdict.REFUTED,
        explanation=(
            f"{c_pass} passage(s) from {c_src} independent source(s) contradict the "
            f"claim (NLI score >= {tau:.2f}); no strong supporting evidence was "
            f"retrieved."
            + (" Corroboration is limited to a single source." if limited else "")
        ),
        limited_corroboration=limited,
        support_passages=0, contradict_passages=c_pass,
        support_sources=0, contradict_sources=c_src, independent_groups=groups,
    )
