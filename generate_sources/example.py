#!/usr/bin/env python3
"""Example: Using the Security Analysis Agent programmatically."""

import asyncio
from pathlib import Path

from scanner import AstGrepScanner
from agent import SecurityAnalysisAgent
from models import RiskLevel


async def main():
    """Example of using the security analysis agent."""

    # Configure paths
    rules_dir = Path(__file__).parent / "rules"
    target_dir = Path("/path/to/your/codebase")  # Change this!

    # Step 1: Scan with ast-grep
    print("Step 1: Scanning with ast-grep...")
    scanner = AstGrepScanner(rules_dir=rules_dir, target_dir=target_dir)
    findings = scanner.scan_all()

    print(f"Found {len(findings)} potential entry points\n")

    if not findings:
        print("No findings. Exiting.")
        return

    # Optionally limit for testing
    findings = findings[:5]  # Just analyze first 5 for demo

    # Step 2: Initialize AI agent
    print("Step 2: Initializing AI agent...")

    # Choose your model:
    # - "openai:gpt-4o" (recommended, requires OPENAI_API_KEY)
    # - "anthropic:claude-3-5-sonnet-20241022" (requires ANTHROPIC_API_KEY)
    # - "openai:gpt-4o-mini" (cheaper, faster)

    agent = SecurityAnalysisAgent(model="openai:gpt-5")

    # Step 3: Analyze findings
    print("Step 3: Analyzing with AI...\n")

    # Code reader function
    def code_reader(file_path: str, line_num: int):
        return scanner.read_code_context(file_path, line_num, context_lines=30)

    # Run analysis
    results = await agent.analyze_all_findings(findings, code_reader)

    # Step 4: Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"\nTotal Analyzed: {results.total_functions_analyzed}")
    print(f"High Priority: {results.high_priority_count}")
    print("\nSummary:")
    print(results.summary)
    print("\nRecommendations:")
    for i, rec in enumerate(results.recommendations, 1):
        print(f"{i}. {rec}")

    print("\n" + "=" * 80)
    print("TOP 5 FINDINGS")
    print("=" * 80)

    for i, finding in enumerate(results.findings[:5], 1):
        print(f"\n[{i}] {finding.risk_level.value.upper()} - {finding.function_name}")
        print(
            f"    Location: {finding.location.file_path}:{finding.location.line_number}"
        )
        print(f"    Framework: {finding.framework}")
        print(f"    Unauthenticated: {finding.accepts_unauthenticated_input}")

        if finding.security_concerns:
            print("    Concerns:")
            for concern in finding.security_concerns:
                print(
                    f"      - {concern.vulnerability_type.value}: {concern.description}"
                )

        print(f"    Reasoning: {finding.reasoning[:200]}...")

    # Step 5: Export to JSON (optional)
    output_path = Path("security-analysis-results.json")
    output_path.write_text(results.model_dump_json(indent=2))
    print(f"\nFull results saved to: {output_path}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
