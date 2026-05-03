"""Phase-3 smart router adapter for Hermes OS.

Bridges Week-3 analyzer contract (`direct`, `direct_with_suggestion`, `fleet`)
into Hermes OS routing contract (`hermes_direct`, `fleet_complex`, `fleet_safety`, `fleet_multi`).

This keeps compatibility by always returning `RoutingDecision` from the
legacy router schema while preserving phase-3 analysis metadata for
suggestion/analyze-only reporting.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from core.router.task_router import TaskRoute, RoutingDecision, TaskRouter
except ImportError:  # pragma: no cover - safe-guard for packaging path issues
    TaskRouter = None  # type: ignore[assignment]
    TaskRoute = None  # type: ignore[assignment]

from v3.analyzer import TaskAnalyzer


class Phase3RoutingAdapter:
    """Adapter that maps v3 analyzer outputs into legacy `RoutingDecision`."""

    SAFETY_KEYWORDS = (
        "delete all",
        "drop table",
        "wipe",
        "erase",
        "rm -rf",
        "credential",
        "secret",
        "password",
        "api key",
        "production",
        "privilege",
        "ransomware",
        "exploit",
    )

    def __init__(
        self,
        analyzer: Optional[TaskAnalyzer] = None,
        legacy_router: Optional[Any] = None,
        contract: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.analyzer = analyzer or TaskAnalyzer()
        self.legacy_router = legacy_router
        self.contract = {
            "fleet_score_threshold": 8,
            "direct_with_suggestion_min": 4,
            "direct_with_suggestion_max": 7,
            "direct_route": TaskRoute.HERMES_DIRECT.value if TaskRoute else "hermes_direct",
            "fleet_route": TaskRoute.FLEET_COMPLEX.value if TaskRoute else "fleet_complex",
            "safety_route": TaskRoute.FLEET_SAFETY.value if TaskRoute else "fleet_safety",
            "multi_route": TaskRoute.FLEET_MULTI_DIVISION.value if TaskRoute else "fleet_multi",
        }
        if contract:
            self.contract.update(contract)

    def analyze(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        context = context or {}

        manual_override = self._normalize_manual_override(context.get("manual_override"))

        # Safety override: keep current behavior when analyzer does not explicitly handle this.
        if self._is_safety_keyword_hit(task_description):
            decision = self._make_decision(
                route=self.contract["safety_route"],
                confidence=1.0,
                reason="Safety-sensitive keyword match detected. Route requires validation.",
                suggested_division=context.get("suggested_division", "DIV-05"),
                estimated_duration="long",
                requires_approval=True,
                raw="fleet",
                source="keyword",
                score=10,
                factors={"keyword_match": 10},
                suggestion="Fleet validation recommended for safety-sensitive task.",
                raw_route="fleet",
            )
            if manual_override == "hermes":
                decision = self._force_direct(decision, note="Manual override requested direct execution.")
            return decision

        # Primary path: v3 analyzer
        try:
            analysis = self.analyzer.analyze(task_description)
            raw_route = self._to_legacy_contract_route(analysis)
            route_value, reason_extra = self._normalize_route(raw_route, task_description, analysis)
            suggested_division = self._suggest_division_from_analysis(analysis)

            confidence = float(analysis.get("confidence", 0.0))
            score = int(analysis.get("score", 0))
            suggestion = analysis.get("suggestion", "") or ""
            factors = analysis.get("factors", {}) or {}

            estimated_duration = "quick"
            if score >= self.contract["fleet_score_threshold"]:
                estimated_duration = "long"
            elif score >= self.contract["direct_with_suggestion_min"]:
                estimated_duration = "medium"

            requires_approval = route_value == self.contract["safety_route"]
            reason = (
                f"Phase-3 analyzer score={score} suggestion='{analysis.get('recommendation')}'. "
                f"{suggestion}"
            )
            if reason_extra:
                reason = f"{reason} {reason_extra}"

            decision = self._make_decision(
                route=route_value,
                confidence=confidence,
                reason=reason.strip(),
                suggested_division=suggested_division,
                estimated_duration=estimated_duration,
                requires_approval=bool(requires_approval),
                raw=raw_route,
                source="v3_analyzer",
                score=score,
                factors=factors,
                suggestion=suggestion,
                raw_route=raw_route,
            )
        except Exception as exc:
            # fallback to legacy router if analyzer fails
            if self.legacy_router:
                return self._bridge_legacy(task_description, context, fallback_error=str(exc))
            # final fallback keeps behavior deterministic even if legacy isn't present
            return self._fallback_decision(task_description, str(exc))

        # Manual override (high priority): explicit /fleet usage should force fleet execution.
        if manual_override == "fleet" and decision.route.value != self.contract["safety_route"]:
            decision = self._force_fleet(decision, note="Manual override requested fleet execution.")
        elif manual_override == "hermes":
            decision = self._force_direct(decision, note="Manual override requested direct execution.")

        return decision

    def _to_legacy_contract_route(self, analysis: Dict[str, Any]) -> str:
        """Normalize v3 analyzer output to contract-level route."""
        recommendation = str(analysis.get("recommendation", "")).strip().lower()
        score = int(analysis.get("score", 0))

        # Keep existing analyzer semantics but enrich direct-with-suggestion band explicitly.
        if recommendation == "fleet" or score >= self.contract["fleet_score_threshold"]:
            return "fleet"
        if score >= self.contract["direct_with_suggestion_min"]:
            return "direct_with_suggestion"
        return "direct"

    def _normalize_route(self, contract_route: str, task: str, analysis: Dict[str, Any]) -> tuple[str, str]:
        route = contract_route
        reason_extra = ""
        if route == "fleet":
            return self.contract["fleet_route"], reason_extra

        if route == "direct_with_suggestion":
            # direct with suggestion still executes via hermes_direct in analyze-only mode.
            # reason should clearly communicate suggestion.
            return self.contract["direct_route"], "(Fleet suggested due complexity band)"

        # direct
        return self.contract["direct_route"], ""

    def _suggest_division_from_analysis(self, analysis: Dict[str, Any]) -> Optional[str]:
        factors = analysis.get("factors", {}) or {}
        if not factors:
            return None

        if factors.get("technical_terms", 0) >= 2 or factors.get("dependencies", 0) >= 2:
            return "DIV-02"
        if factors.get("research", 0) >= 2:
            return "DIV-05"
        return "DIV-04"

    def _is_safety_keyword_hit(self, task_description: str) -> bool:
        text = (task_description or "").lower()
        return any(kw in text for kw in self.SAFETY_KEYWORDS)

    def _normalize_manual_override(self, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        value = value.strip().lower()
        if value in {"fleet", "hermes", "direct", "direct_with_suggestion", "force_fleet", "force_hermes"}:
            if value in {"fleet", "force_fleet"}:
                return "fleet"
            return "hermes"
        return ""

    def _bridge_legacy(self, task_description: str, context: Dict[str, Any], fallback_error: Optional[str] = None) -> RoutingDecision:
        if self.legacy_router is None:
            return self._fallback_decision(task_description, fallback_error or "legacy router unavailable")

        decision = self.legacy_router.analyze(task_description, context)
        # enrich legacy result with phase-3 analysis fields
        setattr(
            decision,
            "_phase3",
            {
                "mode": "fallback",
                "contract_route": "legacy",
                "fallback_error": fallback_error,
            },
        )
        return decision

    def _make_decision(
        self,
        *,
        route: str,
        confidence: float,
        reason: str,
        suggested_division: Optional[str],
        estimated_duration: str,
        requires_approval: bool,
        raw: str,
        source: str,
        score: int,
        factors: Dict[str, Any],
        suggestion: str,
        raw_route: str,
    ) -> RoutingDecision:
        if TaskRoute is None or RoutingDecision is None:  # pragma: no cover
            raise RuntimeError("core.router.task_router unavailable")

        route_enum = TaskRoute(route)
        decision = RoutingDecision(
            route=route_enum,
            confidence=confidence,
            reason=reason,
            suggested_division=suggested_division,
            estimated_duration=estimated_duration,
            requires_approval=requires_approval,
        )
        setattr(
            decision,
            "phase3",
            {
                "raw_route": raw_route,
                "contract_route": raw,
                "normalized_route": route,
                "source": source,
                "score": score,
                "factors": factors,
                "suggestion": suggestion,
            },
        )
        return decision

    def _force_fleet(self, decision: RoutingDecision, note: str = "") -> RoutingDecision:
        if decision.route.value != self.contract["safety_route"]:
            decision.route = TaskRoute(self.contract["fleet_route"])
            decision.reason = f"{decision.reason} {note}".strip()
        if getattr(decision, "requires_approval", False) is False:
            decision.requires_approval = decision.route.value in {
                self.contract["safety_route"],
            }
        phase3 = getattr(decision, "phase3", {})
        phase3["force_route"] = "fleet"
        decision.phase3 = phase3
        return decision

    def _force_direct(self, decision: RoutingDecision, note: str = "") -> RoutingDecision:
        decision.route = TaskRoute(self.contract["direct_route"])
        decision.reason = f"{decision.reason} {note}".strip()
        phase3 = getattr(decision, "phase3", {})
        phase3["force_route"] = "hermes_direct"
        decision.phase3 = phase3
        return decision

    def _fallback_decision(self, task: str, reason: str) -> RoutingDecision:
        if TaskRoute is None or RoutingDecision is None:  # pragma: no cover
            raise RuntimeError("core.router.task_router unavailable")
        return RoutingDecision(
            route=TaskRoute.HERMES_DIRECT if TaskRoute else "hermes_direct",  # type: ignore[arg-type]
            confidence=0.5,
            reason=f"Router fallback triggered ({reason}).",  # noqa: E501
            suggested_division=None,
            estimated_duration="quick",
            requires_approval=False,
        )
