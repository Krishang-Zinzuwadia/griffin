"""
Main — CLI Entry Point for AI Office Chain

Usage:
    python -m ML.main "Create a Snake game with HTML/CSS/JS"
    python -m ML.main   (interactive prompt)
"""

import sys
import json
import time
from colorama import init as colorama_init, Fore, Style
from .graph import build_graph
from .logger import setup_logging, get_logger
from .utils import reset_token_usage_log, get_token_usage_summary


def main():
    # ── Fix Windows encoding (cp1252 can't handle Unicode/emojis) ─
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    colorama_init()  # Enable colors on Windows

    # ── Initialize structured logging ────────────────────────────
    setup_logging()
    logger = get_logger("main")

    print(f"\n{Fore.WHITE}{Style.BRIGHT}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          🏢  AI OFFICE CHAIN  —  Multi-Agent System     ║")
    print("║          using Sequential LangGraph (A2A)                ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")

    # ── Get project goal ─────────────────────────────────────────
    if len(sys.argv) > 1:
        project_goal = " ".join(sys.argv[1:])
    else:
        project_goal = input(f"{Fore.CYAN}  Enter your project idea: {Style.RESET_ALL}").strip()

    if not project_goal:
        print(f"{Fore.RED}  ❌ No project goal provided. Exiting.{Style.RESET_ALL}")
        sys.exit(1)

    logger.info(f"Pipeline starting | Goal: {project_goal}")
    print(f"\n{Fore.WHITE}  📋 Goal: {project_goal}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}  ⏱️  Starting pipeline...{Style.RESET_ALL}\n")

    start_time = time.time()

    # ── Reset token usage tracker for this session ────────────────
    reset_token_usage_log()

    # ── Build & run the graph ────────────────────────────────────
    chain = build_graph()
    logger.info("Graph compiled successfully")

    initial_state = {
        "project_goal": project_goal,
        "project_name": "",
        "active_offices": [],
        "file_manifest": [],
        "file_descriptions": {},
        "requirements": [],
        "tech_stack": {},
        "folder_structure": "",
        "file_categories": {},
        "design_system": {},
        "api_schema": {},
        "codebase": {},
        "execution_logs": [],
        "github_url": "",
        "token_usage": {},
    }

    final_state = chain.invoke(initial_state)

    #Summary 
    elapsed = time.time() - start_time
    logger.info(f"Pipeline complete | Elapsed: {elapsed:.2f}s")

    print(f"\n{Fore.GREEN}{Style.BRIGHT}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                    ✅  PIPELINE COMPLETE                ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")

    print(f"  {Fore.WHITE}⏱️  Time elapsed: {elapsed:.1f}s{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}📁 Files created: {len(final_state.get('codebase', {}))}{Style.RESET_ALL}")

    github_url = final_state.get("github_url", "")
    if github_url:
        print(f"  {Fore.GREEN}🔗 GitHub URL: {github_url}{Style.RESET_ALL}")
        logger.info(f"GitHub URL: {github_url}")
    else:
        print(f"  {Fore.YELLOW}📁 Project saved locally in sandbox/{Style.RESET_ALL}")
        logger.info("Project saved locally (no GitHub push)")

    # ── Execution Logs ───────────────────────────────────────────
    print(f"\n{Fore.WHITE}  📝 Execution Log:{Style.RESET_ALL}")
    for log in final_state.get("execution_logs", []):
        print(f"     {log}")
        logger.info(f"Execution log: {log}")

    # ── Token Usage & Cost Summary ───────────────────────────────
    usage_summary = get_token_usage_summary()
    print(f"\n{Fore.CYAN}{Style.BRIGHT}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║               💰  TOKEN USAGE & COST SUMMARY           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}📊 Total LLM calls:   {usage_summary['total_calls']}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}📥 Input tokens:      {usage_summary['total_input_tokens']:,}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}📤 Output tokens:     {usage_summary['total_output_tokens']:,}{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}💵 Total cost:        ${usage_summary['total_cost_usd']:.6f}{Style.RESET_ALL}")

    if usage_summary.get("per_office"):
        print(f"\n  {Fore.CYAN}Per-Office Breakdown:{Style.RESET_ALL}")
        for office, stats in usage_summary["per_office"].items():
            print(
                f"     {office:30s}  calls={stats['calls']:2d}  "
                f"in={stats['input_tokens']:6,}  out={stats['output_tokens']:6,}  "
                f"cost=${stats['cost_usd']:.6f}  time={stats['total_latency_s']:.1f}s"
            )

    logger.info(f"Token usage summary: {json.dumps(usage_summary)}")

    print()
    logger.info("=== Pipeline session ended ===")


if __name__ == "__main__":
    main()
