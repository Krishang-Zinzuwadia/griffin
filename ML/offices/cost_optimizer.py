"""
Cost Optimizer Office — Token Usage & Cost Tracking

Monitors token consumption across all offices, calculates per-call
costs for the Gemini API, and recommends the most efficient execution
path by analysing which offices are worth their token spend.

Pricing is based on the Gemini API published rates and adjusts
dynamically based on the model configured in ML/config.py.
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm, LLM_MODEL, LLM_PROVIDER
from ..utils import invoke_and_parse_json
from ..logger import get_logger

logger = get_logger("cost_optimizer")

# ═══════════════════════════════════════════════════════════════════
# GEMINI PRICING — per 1 million tokens (USD)
# Source: https://ai.google.dev/pricing
# ═══════════════════════════════════════════════════════════════════

GEMINI_PRICING: dict[str, dict[str, float]] = {
    # model-pattern → { input_per_1m, output_per_1m }
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.0-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.0-pro": {"input": 0.50, "output": 1.50},
}

# OpenRouter pricing (rough estimates — varies by model)
OPENROUTER_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.0-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "default": {"input": 0.50, "output": 1.50},
}

# Average token counts per office (empirical estimates for budget forecasting)
OFFICE_AVG_TOKENS: dict[str, dict[str, int]] = {
    "ceo_office": {"input": 800, "output": 600},
    "product_manager": {"input": 700, "output": 500},
    "architect": {"input": 900, "output": 800},
    "ui_designer": {"input": 600, "output": 400},
    "api_designer": {"input": 700, "output": 600},
    "frontend_engineer": {"input": 1200, "output": 2000},  # per file
    "backend_engineer": {"input": 1200, "output": 2000},   # per file
    "database_engineer": {"input": 1000, "output": 1500},  # per file
    "qa_engineer": {"input": 1500, "output": 2000},
    "security_officer": {"input": 1500, "output": 1000},
    "tech_writer": {"input": 1200, "output": 1500},
}


def _get_pricing() -> dict[str, float]:
    """Return the { input, output } pricing per 1M tokens for the active model."""
    pricing_table = (
        GEMINI_PRICING if LLM_PROVIDER == "gemini" else OPENROUTER_PRICING
    )
    model_lower = LLM_MODEL.lower()

    for pattern, rates in pricing_table.items():
        if pattern in model_lower:
            return rates

    # Fallback
    return pricing_table.get("default", {"input": 0.50, "output": 1.50})


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English text."""
    return max(1, len(text) // 4)


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for a given token count."""
    pricing = _get_pricing()
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def estimate_office_cost(office_id: str, file_count: int = 1) -> dict:
    """Estimate cost for a single office run.

    Args:
        office_id: The office identifier.
        file_count: Number of files (for coding offices, each file = 1 LLM call).

    Returns:
        Dict with estimated input_tokens, output_tokens, cost_usd.
    """
    averages = OFFICE_AVG_TOKENS.get(office_id, {"input": 800, "output": 600})
    coding_offices = {"frontend_engineer", "backend_engineer", "database_engineer"}

    multiplier = file_count if office_id in coding_offices else 1

    input_tokens = averages["input"] * multiplier
    output_tokens = averages["output"] * multiplier
    cost = calculate_cost(input_tokens, output_tokens)

    return {
        "office_id": office_id,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_calls": multiplier,
        "estimated_cost_usd": cost,
    }


def estimate_pipeline_cost(
    active_offices: list[str],
    file_categories: dict[str, str],
) -> dict:
    """Estimate total pipeline cost across all active offices.

    Args:
        active_offices: List of office IDs the CEO selected.
        file_categories: Map of file path → category.

    Returns:
        Dict with per-office breakdowns and totals.
    """
    # Count files per coding office
    category_to_office = {
        "frontend": "frontend_engineer",
        "backend": "backend_engineer",
        "database": "database_engineer",
    }
    file_counts: dict[str, int] = {}
    for _path, cat in file_categories.items():
        office = category_to_office.get(cat)
        if office:
            file_counts[office] = file_counts.get(office, 0) + 1

    breakdowns = []
    total_input = 0
    total_output = 0
    total_cost = 0.0
    total_calls = 0

    # CEO always runs
    ceo_est = estimate_office_cost("ceo_office")
    breakdowns.append(ceo_est)
    total_input += ceo_est["estimated_input_tokens"]
    total_output += ceo_est["estimated_output_tokens"]
    total_cost += ceo_est["estimated_cost_usd"]
    total_calls += ceo_est["estimated_calls"]

    for office_id in active_offices:
        fc = file_counts.get(office_id, 1)
        est = estimate_office_cost(office_id, file_count=fc)
        breakdowns.append(est)
        total_input += est["estimated_input_tokens"]
        total_output += est["estimated_output_tokens"]
        total_cost += est["estimated_cost_usd"]
        total_calls += est["estimated_calls"]

    return {
        "model": LLM_MODEL,
        "provider": LLM_PROVIDER,
        "pricing_per_1m": _get_pricing(),
        "office_breakdowns": breakdowns,
        "total_estimated_input_tokens": total_input,
        "total_estimated_output_tokens": total_output,
        "total_estimated_calls": total_calls,
        "total_estimated_cost_usd": round(total_cost, 6),
    }


def find_efficient_path(
    active_offices: list[str],
    file_categories: dict[str, str],
    budget_usd: float | None = None,
) -> dict:
    """Analyse office selections and recommend the most cost-efficient path.

    If a budget is provided, offices are pruned by priority until the
    projected cost fits within the budget. Priority order (low → high risk
    of removal):
        architect > coding engineers > product_manager > ui_designer >
        api_designer > qa_engineer > security_officer > tech_writer

    Returns:
        Dict with recommended offices, estimated savings, and reasoning.
    """
    # Priority: lower number = harder to cut
    PRIORITY: dict[str, int] = {
        "architect": 1,
        "frontend_engineer": 2,
        "backend_engineer": 2,
        "database_engineer": 2,
        "product_manager": 3,
        "ui_designer": 4,
        "api_designer": 4,
        "qa_engineer": 5,
        "security_officer": 5,
        "tech_writer": 6,
    }

    full_estimate = estimate_pipeline_cost(active_offices, file_categories)
    full_cost = full_estimate["total_estimated_cost_usd"]

    if budget_usd is None or full_cost <= budget_usd:
        return {
            "recommended_offices": active_offices,
            "removed_offices": [],
            "original_cost_usd": full_cost,
            "optimized_cost_usd": full_cost,
            "savings_usd": 0.0,
            "reasoning": "All offices fit within budget. No optimisation needed.",
        }

    # Sort offices by priority (highest number = first to cut)
    sorted_offices = sorted(
        active_offices,
        key=lambda o: PRIORITY.get(o, 10),
        reverse=True,
    )

    recommended = list(active_offices)
    removed = []

    for office_id in sorted_offices:
        if office_id == "architect":
            continue  # Never remove architect
        # Check if removing this office brings us under budget
        test_offices = [o for o in recommended if o != office_id]
        test_estimate = estimate_pipeline_cost(test_offices, file_categories)

        if test_estimate["total_estimated_cost_usd"] <= budget_usd:
            recommended = test_offices
            removed.append(office_id)
            break
        else:
            recommended = test_offices
            removed.append(office_id)
            if estimate_pipeline_cost(recommended, file_categories)["total_estimated_cost_usd"] <= budget_usd:
                break

    optimized_cost = estimate_pipeline_cost(recommended, file_categories)["total_estimated_cost_usd"]

    return {
        "recommended_offices": recommended,
        "removed_offices": removed,
        "original_cost_usd": full_cost,
        "optimized_cost_usd": optimized_cost,
        "savings_usd": round(full_cost - optimized_cost, 6),
        "reasoning": (
            f"Removed {', '.join(removed)} to fit within ${budget_usd:.4f} budget. "
            f"Savings: ${full_cost - optimized_cost:.6f}."
        ),
    }


# ═══════════════════════════════════════════════════════════════════
# COST OPTIMIZER OFFICE NODE
# ═══════════════════════════════════════════════════════════════════

COST_OPTIMIZER_SYSTEM = """You are the Cost Optimizer for an AI software company.
You analyse the planned pipeline and recommend the most efficient execution path.

You must respond with ONLY valid JSON (no markdown, no code fences, no extra text).

Response format:
{{
  "analysis": {{
    "total_offices": 5,
    "total_estimated_tokens": 15000,
    "total_estimated_cost_usd": 0.0045,
    "cost_per_office": [
      {{ "office": "architect", "tokens": 1700, "cost_usd": 0.0005, "essential": true }},
      {{ "office": "frontend_engineer", "tokens": 6400, "cost_usd": 0.002, "essential": true }}
    ]
  }},
  "recommendations": [
    "The pipeline is cost-efficient for this project scope.",
    "Consider removing tech_writer for simple projects to save ~$0.0005."
  ],
  "efficiency_score": 85
}}

Rules:
- Analyse the active offices and file manifest to estimate token usage
- Score efficiency from 0-100 (100 = optimal cost-to-value ratio)
- Flag any offices that may be unnecessary for this project type
- Consider that coding offices scale with file count
- Be concise and actionable in recommendations
"""

COST_OPTIMIZER_HUMAN = """Project: {project_name}
Goal: {project_goal}
Active Offices: {active_offices}
File Manifest ({file_count} files): {file_manifest}
File Categories: {file_categories}

Current Token Usage So Far: {current_token_usage}
Estimated Remaining Cost: ${estimated_remaining_cost}

Analyse the cost efficiency and provide recommendations. Return ONLY the JSON object."""


def cost_optimizer_office(state: OfficeState) -> dict:
    """Cost Optimizer node: analyse token usage and recommend efficient paths."""

    logger.info("=== COST OPTIMIZER OFFICE — Entering ===")
    office_start = time.time()

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"  💰  COST OPTIMIZER OFFICE — Token & Cost Analysis")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    active_offices = state.get("active_offices", [])
    file_categories = state.get("file_categories", {})
    file_manifest = state.get("file_manifest", [])
    token_usage = state.get("token_usage", {})

    # ── Calculate estimates ──────────────────────────────────────
    pipeline_estimate = estimate_pipeline_cost(active_offices, file_categories)

    # ── Calculate actual usage so far ────────────────────────────
    actual_input = token_usage.get("total_input_tokens", 0)
    actual_output = token_usage.get("total_output_tokens", 0)
    actual_cost = token_usage.get("total_cost_usd", 0.0)
    calls_made = token_usage.get("total_calls", 0)

    # ── Print summary ────────────────────────────────────────────
    print(f"  {Fore.WHITE}📊 Model: {LLM_MODEL} ({LLM_PROVIDER}){Style.RESET_ALL}")
    pricing = _get_pricing()
    print(f"  {Fore.WHITE}💵 Pricing: ${pricing['input']}/1M input, ${pricing['output']}/1M output{Style.RESET_ALL}\n")

    print(f"  {Fore.GREEN}── Actual Usage (so far) ──{Style.RESET_ALL}")
    print(f"     Calls made:    {calls_made}")
    print(f"     Input tokens:  {actual_input:,}")
    print(f"     Output tokens: {actual_output:,}")
    print(f"     Cost:          ${actual_cost:.6f}")

    print(f"\n  {Fore.YELLOW}── Estimated Total Pipeline ──{Style.RESET_ALL}")
    print(f"     Total calls:   {pipeline_estimate['total_estimated_calls']}")
    print(f"     Input tokens:  {pipeline_estimate['total_estimated_input_tokens']:,}")
    print(f"     Output tokens: {pipeline_estimate['total_estimated_output_tokens']:,}")
    print(f"     Est. cost:     ${pipeline_estimate['total_estimated_cost_usd']:.6f}")

    print(f"\n  {Fore.CYAN}── Per-Office Breakdown ──{Style.RESET_ALL}")
    for breakdown in pipeline_estimate["office_breakdowns"]:
        oid = breakdown["office_id"]
        est_cost = breakdown["estimated_cost_usd"]
        est_calls = breakdown["estimated_calls"]
        print(
            f"     {oid:25s}  calls={est_calls:2d}  "
            f"tokens={breakdown['estimated_input_tokens'] + breakdown['estimated_output_tokens']:6,}  "
            f"cost=${est_cost:.6f}"
        )

    # ── Find efficient path ──────────────────────────────────────
    efficiency = find_efficient_path(active_offices, file_categories)

    if efficiency["removed_offices"]:
        print(f"\n  {Fore.YELLOW}⚡ Efficiency Recommendation:{Style.RESET_ALL}")
        print(f"     Could remove: {', '.join(efficiency['removed_offices'])}")
        print(f"     Savings:      ${efficiency['savings_usd']:.6f}")
    else:
        print(f"\n  {Fore.GREEN}✅ Pipeline is already cost-efficient.{Style.RESET_ALL}")

    # ── Optional: ask LLM for deeper analysis ────────────────────
    llm_analysis = {}
    try:
        llm = get_llm(temperature=0.2)
        current_usage_str = json.dumps(token_usage, indent=2) if token_usage else "(no usage yet)"
        messages = [
            ("system", COST_OPTIMIZER_SYSTEM),
            ("human", COST_OPTIMIZER_HUMAN.format(
                project_name=state.get("project_name", ""),
                project_goal=state.get("project_goal", ""),
                active_offices=json.dumps(active_offices),
                file_count=len(file_manifest),
                file_manifest=json.dumps(file_manifest[:20]),  # Cap to avoid huge prompts
                file_categories=json.dumps(file_categories),
                current_token_usage=current_usage_str,
                estimated_remaining_cost=f"{pipeline_estimate['total_estimated_cost_usd']:.6f}",
            )),
        ]

        llm_analysis = invoke_and_parse_json(
            llm, messages,
            max_retries=2,
            office_name="COST_OPTIMIZER",
        )

        recommendations = llm_analysis.get("recommendations", [])
        efficiency_score = llm_analysis.get("efficiency_score", 0)

        print(f"\n  {Fore.GREEN}🧠 AI Analysis (Efficiency Score: {efficiency_score}/100):{Style.RESET_ALL}")
        for rec in recommendations:
            print(f"     • {rec}")

    except Exception as e:
        logger.warning(f"LLM analysis failed (non-critical): {e}")
        print(f"  {Fore.YELLOW}⚠️  LLM analysis skipped (non-critical){Style.RESET_ALL}")

    elapsed = time.time() - office_start

    # ── Build result ─────────────────────────────────────────────
    cost_report = {
        "model": LLM_MODEL,
        "provider": LLM_PROVIDER,
        "pricing_per_1m_tokens": pricing,
        "actual_usage": {
            "total_input_tokens": actual_input,
            "total_output_tokens": actual_output,
            "total_cost_usd": actual_cost,
            "total_calls": calls_made,
        },
        "estimated_pipeline": pipeline_estimate,
        "efficiency": efficiency,
        "llm_analysis": llm_analysis,
    }

    log_msg = (
        f"[COST_OPTIMIZER] Analysed pipeline: "
        f"{len(active_offices)} offices, "
        f"est. ${pipeline_estimate['total_estimated_cost_usd']:.6f}, "
        f"actual so far ${actual_cost:.6f}. ({elapsed:.1f}s)"
    )
    logger.info(f"=== COST OPTIMIZER OFFICE — Exiting ({elapsed:.2f}s) ===")

    print(f"\n  {Fore.GREEN}✅ Cost analysis complete ({elapsed:.1f}s){Style.RESET_ALL}\n")

    return {
        "token_usage": {
            **token_usage,
            "cost_report": cost_report,
        },
        "execution_logs": [log_msg],
    }
