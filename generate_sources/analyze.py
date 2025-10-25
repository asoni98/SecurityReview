#!/usr/bin/env python3
"""
Security Analysis Tool for User Input Handlers

Uses ast-grep to find API route handlers and other user input entry points,
then analyzes them with AI to prioritize security review efforts.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from scanner import AstGrepScanner
from agent import SecurityTriageAgent
from models import RiskLevel

try:
    from deployment_parser import DeploymentModelParser
except ImportError:
    DeploymentModelParser = None


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="AI-powered security analysis of user input handlers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze current directory with OpenAI GPT-4
  %(prog)s --target . --model openai:gpt-5

  # Analyze specific project with Claude
  %(prog)s --target /path/to/project --model anthropic:claude-3-5-sonnet-20241022

  # Save results to JSON file
  %(prog)s --target . --output results.json

  # Limit analysis to high-risk findings only
  %(prog)s --target . --min-risk high

Environment Variables:
  OPENAI_API_KEY     - OpenAI API key (for openai: models)
  ANTHROPIC_API_KEY  - Anthropic API key (for anthropic: models)
        """,
    )

    parser.add_argument(
        "--target",
        type=Path,
        default=Path.cwd(),
        help="Target codebase directory to analyze (default: current directory)",
    )

    parser.add_argument(
        "--rules",
        type=Path,
        default=None,
        help="Directory containing ast-grep rules (default: ./rules)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="openai:gpt-5",
        help="AI model to use (default: openai:gpt-5, also: anthropic:claude-3-5-sonnet-20241022)",
    )

    parser.add_argument(
        "--output", "-o", type=Path, help="Output file for results (JSON format)"
    )

    parser.add_argument(
        "--format",
        choices=["json", "jsonl", "markdown", "text"],
        default="text",
        help="Output format (default: text). Use 'jsonl' for streaming JSON Lines output.",
    )

    parser.add_argument(
        "--min-risk",
        choices=["critical", "high", "medium", "low", "info"],
        default="info",
        help="Minimum risk level to include in output (default: info)",
    )

    parser.add_argument(
        "--max-findings",
        type=int,
        help="Maximum number of findings to analyze (for testing)",
    )

    parser.add_argument(
        "--context-lines",
        type=int,
        default=30,
        help="Lines of code context to analyze around each finding (default: 30)",
    )

    parser.add_argument(
        "--max-real-handlers",
        type=int,
        help="Stop after finding this many real handlers (useful to limit GPT-5 calls)",
    )

    parser.add_argument(
        "--deployment-model",
        type=Path,
        help="Path to deployment model JSON file for enriching findings with infrastructure context",
    )

    parser.add_argument(
        "--debug-deployment",
        action="store_true",
        help="Enable debug logging for deployment context matching",
    )

    return parser.parse_args()


def format_output_text(findings, args):
    """Format findings as human-readable text."""
    output = []

    # Header
    output.append("=" * 80)
    output.append("SECURITY TRIAGE REPORT - USER INPUT HANDLERS")
    output.append("=" * 80)
    output.append("")

    # Summary
    output.append("TRIAGE SUMMARY")
    output.append("-" * 80)
    output.append(findings.summary)
    output.append("")

    # Statistics
    output.append("STATISTICS")
    output.append("-" * 80)
    output.append(f"Total Functions Analyzed: {findings.total_functions_analyzed}")
    output.append(f"High Priority (CRITICAL + HIGH): {findings.high_priority_count}")
    output.append("")

    risk_counts = {}
    for analysis in findings.findings:
        risk_counts[analysis.risk_level] = risk_counts.get(analysis.risk_level, 0) + 1

    output.append("Risk Level Breakdown:")
    for risk_level in [
        RiskLevel.CRITICAL,
        RiskLevel.HIGH,
        RiskLevel.MEDIUM,
        RiskLevel.LOW,
        RiskLevel.INFO,
    ]:
        count = risk_counts.get(risk_level, 0)
        output.append(f"  {risk_level.value.upper():8s}: {count}")
    output.append("")

    # Recommendations
    if findings.recommendations:
        output.append("RECOMMENDATIONS")
        output.append("-" * 80)
        for i, rec in enumerate(findings.recommendations, 1):
            output.append(f"{i}. {rec}")
        output.append("")

    # Filter findings by minimum risk level
    # By default, exclude INFO (false positives) unless user explicitly requested them
    risk_order = {
        RiskLevel.CRITICAL: 0,
        RiskLevel.HIGH: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 3,
        RiskLevel.INFO: 4,
    }

    # Default to LOW if user didn't specify, to exclude INFO
    default_min_risk = "low" if args.min_risk == "info" else args.min_risk
    min_risk_level = RiskLevel(default_min_risk)
    min_risk_value = risk_order[min_risk_level]

    filtered_findings = [
        f for f in findings.findings if risk_order[f.risk_level] <= min_risk_value
    ]

    # Count how many were filtered out as false positives
    false_positives_count = sum(
        1 for f in findings.findings if f.risk_level == RiskLevel.INFO
    )

    # Detailed Findings
    if false_positives_count > 0:
        output.append(
            f"DETAILED FINDINGS (Showing {len(filtered_findings)} real handlers, filtered {false_positives_count} false positives)"
        )
    else:
        output.append(
            f"DETAILED FINDINGS (Showing {len(filtered_findings)}/{len(findings.findings)})"
        )
    output.append("=" * 80)
    output.append("")

    if len(filtered_findings) == 0:
        output.append("No user input handlers found at the requested priority level.")
        output.append("")
        if false_positives_count > 0:
            output.append(
                f"Note: {false_positives_count} items were identified as false positives (config, tests, utilities)."
            )
            output.append("Use --min-risk info to see them.")
        output.append("")
        return "\n".join(output)

    for i, analysis in enumerate(filtered_findings, 1):
        output.append(
            f"[{i}] {analysis.risk_level.value.upper()} - {analysis.function_name}"
        )
        output.append("-" * 80)
        output.append(
            f"Location: {analysis.location.file_path}:{analysis.location.line_number}"
        )
        output.append(f"Framework: {analysis.framework} ({analysis.language})")

        if analysis.endpoint_path:
            output.append(f"Endpoint: {analysis.endpoint_path}")

        if analysis.http_methods:
            output.append(f"Methods: {', '.join(analysis.http_methods)}")

        output.append(
            f"Unauthenticated Input: {'YES' if analysis.accepts_unauthenticated_input else 'NO'}"
        )

        if analysis.input_sources:
            sources = ", ".join(s.value for s in analysis.input_sources)
            output.append(f"Input Sources: {sources}")

        # Display deployment context if available
        if analysis.deployment_context:
            output.append("")
            output.append("Deployment Context:")
            ctx = analysis.deployment_context
            if ctx.service_name:
                output.append(f"  Service: {ctx.service_name}")
            if ctx.trust_zone:
                output.append(f"  Trust Zone: {ctx.trust_zone}")
            if ctx.network_exposure:
                output.append(f"  Network Exposure: {ctx.network_exposure}")
            if ctx.deployment_target:
                output.append(f"  Deployment Target: {ctx.deployment_target}")
            if ctx.authentication_method:
                output.append(f"  Auth Method: {ctx.authentication_method}")
            if ctx.upstream_services:
                output.append(f"  Upstream: {', '.join(ctx.upstream_services)}")
            if ctx.downstream_services:
                output.append(f"  Downstream: {', '.join(ctx.downstream_services)}")

        output.append("")
        output.append("Security Assessment:")

        if analysis.security_concerns:
            output.append("  Concerns:")
            for concern in analysis.security_concerns:
                conf_pct = int(concern.confidence * 100)
                output.append(
                    f"    - [{concern.vulnerability_type.value}] {concern.description} ({conf_pct}% confidence)"
                )
        else:
            output.append("  No specific concerns identified")

        output.append("")
        output.append("  Security Controls:")
        output.append(
            f"    Input Validation: {'Present' if analysis.has_input_validation else 'Missing' if analysis.has_input_validation is False else 'Unknown'}"
        )
        output.append(
            f"    Sanitization: {'Present' if analysis.has_sanitization else 'Missing' if analysis.has_sanitization is False else 'Unknown'}"
        )
        output.append(
            f"    Authorization: {'Present' if analysis.has_authorization_check else 'Missing' if analysis.has_authorization_check is False else 'Unknown'}"
        )

        output.append("")
        output.append("Reasoning:")
        output.append(f"  {analysis.reasoning}")

        output.append("")
        output.append("")

    return "\n".join(output)


def format_output_markdown(findings, args):
    """Format findings as Markdown."""
    output = []

    output.append("# Security Analysis Report - User Input Handlers\n")

    # Summary
    output.append("## Executive Summary\n")
    output.append(findings.summary + "\n")

    # Statistics
    output.append("## Statistics\n")
    output.append(
        f"- **Total Functions Analyzed**: {findings.total_functions_analyzed}"
    )
    output.append(
        f"- **High Priority (CRITICAL + HIGH)**: {findings.high_priority_count}\n"
    )

    risk_counts = {}
    for analysis in findings.findings:
        risk_counts[analysis.risk_level] = risk_counts.get(analysis.risk_level, 0) + 1

    output.append("### Risk Level Breakdown\n")
    for risk_level in [
        RiskLevel.CRITICAL,
        RiskLevel.HIGH,
        RiskLevel.MEDIUM,
        RiskLevel.LOW,
        RiskLevel.INFO,
    ]:
        count = risk_counts.get(risk_level, 0)
        output.append(f"- **{risk_level.value.upper()}**: {count}")
    output.append("")

    # Recommendations
    if findings.recommendations:
        output.append("## Recommendations\n")
        for i, rec in enumerate(findings.recommendations, 1):
            output.append(f"{i}. {rec}")
        output.append("")

    # Detailed Findings
    risk_order = {
        RiskLevel.CRITICAL: 0,
        RiskLevel.HIGH: 1,
        RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 3,
        RiskLevel.INFO: 4,
    }

    # Default to LOW if user didn't specify, to exclude INFO
    default_min_risk = "low" if args.min_risk == "info" else args.min_risk
    min_risk_level = RiskLevel(default_min_risk)
    min_risk_value = risk_order[min_risk_level]

    filtered_findings = [
        f for f in findings.findings if risk_order[f.risk_level] <= min_risk_value
    ]

    false_positives_count = sum(
        1 for f in findings.findings if f.risk_level == RiskLevel.INFO
    )

    output.append("## Detailed Findings\n")

    if len(filtered_findings) == 0:
        output.append("No user input handlers found at the requested priority level.\n")
        if false_positives_count > 0:
            output.append(
                f"*Note: {false_positives_count} items were identified as false positives (config, tests, utilities). Use `--min-risk info` to see them.*\n"
            )
        return "\n".join(output)

    for i, analysis in enumerate(filtered_findings, 1):
        risk_emoji = {
            RiskLevel.CRITICAL: "🔴",
            RiskLevel.HIGH: "🟠",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.LOW: "🔵",
            RiskLevel.INFO: "⚪",
        }

        output.append(
            f"### {risk_emoji[analysis.risk_level]} [{i}] {analysis.function_name}\n"
        )
        output.append(f"**Risk Level**: {analysis.risk_level.value.upper()}  ")
        output.append(
            f"**Location**: `{analysis.location.file_path}:{analysis.location.line_number}`  "
        )
        output.append(f"**Framework**: {analysis.framework} ({analysis.language})  ")

        if analysis.endpoint_path:
            output.append(f"**Endpoint**: `{analysis.endpoint_path}`  ")

        if analysis.http_methods:
            output.append(f"**Methods**: {', '.join(analysis.http_methods)}  ")

        output.append(
            f"**Unauthenticated**: {'YES ⚠️' if analysis.accepts_unauthenticated_input else 'NO ✓'}  "
        )

        if analysis.input_sources:
            sources = ", ".join(f"`{s.value}`" for s in analysis.input_sources)
            output.append(f"**Input Sources**: {sources}  ")

        # Display deployment context if available
        if analysis.deployment_context:
            output.append("")
            output.append("**Deployment Context**:  ")
            ctx = analysis.deployment_context
            if ctx.service_name:
                output.append(f"- Service: `{ctx.service_name}`")
            if ctx.trust_zone:
                output.append(f"- Trust Zone: {ctx.trust_zone}")
            if ctx.network_exposure:
                output.append(f"- Network Exposure: {ctx.network_exposure}")
            if ctx.deployment_target:
                output.append(f"- Deployment Target: {ctx.deployment_target}")
            if ctx.authentication_method:
                output.append(f"- Auth Method: {ctx.authentication_method}")
            if ctx.upstream_services:
                output.append(f"- Upstream Services: {', '.join(f'`{s}`' for s in ctx.upstream_services)}")
            if ctx.downstream_services:
                output.append(f"- Downstream Services: {', '.join(f'`{s}`' for s in ctx.downstream_services)}")

        output.append("")

        if analysis.security_concerns:
            output.append("**Security Concerns**:\n")
            for concern in analysis.security_concerns:
                conf_pct = int(concern.confidence * 100)
                output.append(
                    f"- **{concern.vulnerability_type.value}**: {concern.description} ({conf_pct}% confidence)"
                )
            output.append("")

        output.append("**Security Controls**:\n")
        output.append(
            f"- Input Validation: {'✓ Present' if analysis.has_input_validation else '✗ Missing' if analysis.has_input_validation is False else '? Unknown'}"
        )
        output.append(
            f"- Sanitization: {'✓ Present' if analysis.has_sanitization else '✗ Missing' if analysis.has_sanitization is False else '? Unknown'}"
        )
        output.append(
            f"- Authorization: {'✓ Present' if analysis.has_authorization_check else '✗ Missing' if analysis.has_authorization_check is False else '? Unknown'}"
        )
        output.append("")

        output.append(f"**Analysis**: {analysis.reasoning}\n")
        output.append("---\n")

    return "\n".join(output)


async def main():
    """Main entry point."""
    args = parse_args()

    # Determine rules directory
    if args.rules:
        rules_dir = args.rules
    else:
        # Default to ./rules relative to this script
        rules_dir = Path(__file__).parent / "rules"

    if not rules_dir.exists():
        print(f"Error: Rules directory not found: {rules_dir}", file=sys.stderr)
        print("Please specify --rules or ensure ./rules exists", file=sys.stderr)
        sys.exit(1)

    if not args.target.exists():
        print(f"Error: Target directory not found: {args.target}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("Security Analysis Tool - User Input Handlers")
    print("=" * 80)
    print(f"Target: {args.target}")
    print(f"Rules: {rules_dir}")
    print(f"Model: {args.model}")
    print(f"Context: {args.context_lines} lines")
    print("")

    # Step 1: Scan with ast-grep
    print("STEP 1: Scanning codebase with ast-grep")
    print("-" * 80)

    scanner = AstGrepScanner(rules_dir=rules_dir, target_dir=args.target)
    findings = scanner.scan_all()

    if not findings:
        print("No findings detected. Exiting.")
        return

    print(f"Found {len(findings)} potential user input handlers\n")

    # Deduplicate findings by file:line to avoid analyzing the same location multiple times
    seen_locations = set()
    unique_findings = []
    duplicates_removed = 0

    for finding in findings:
        location_key = f"{finding.file_path}:{finding.line_number}"
        if location_key not in seen_locations:
            seen_locations.add(location_key)
            unique_findings.append(finding)
        else:
            duplicates_removed += 1

    if duplicates_removed > 0:
        print(f"Removed {duplicates_removed} duplicate findings (same file:line)")
        print(f"Unique findings: {len(unique_findings)}\n")

    findings = unique_findings

    # Limit findings if requested
    if args.max_findings and len(findings) > args.max_findings:
        print(
            f"Limiting analysis to first {args.max_findings} findings (--max-findings)"
        )
        findings = findings[: args.max_findings]

    # Step 2: Triage with AI
    print("STEP 2: Triaging findings with AI")
    print("-" * 80)

    # Parse deployment model if provided
    deployment_parser = None
    if args.deployment_model:
        if not DeploymentModelParser:
            print("Warning: deployment_parser module not available, skipping deployment context enrichment")
        elif not args.deployment_model.exists():
            print(f"Warning: Deployment model file not found: {args.deployment_model}")
        else:
            print(f"Loading deployment model from: {args.deployment_model}")
            deployment_parser = DeploymentModelParser(
                args.deployment_model,
                debug=args.debug_deployment
            )
            print(f"  Found {len(deployment_parser.services)} services")
            print(f"  Found {len(deployment_parser.trust_zones)} trust zones")
            if args.debug_deployment:
                print("\n  Service repository paths:")
                for svc_name, svc_info in deployment_parser.services.items():
                    paths = svc_info.get('repository_paths', [])
                    if paths:
                        print(f"    {svc_name}: {paths}")
            print("")

    agent = SecurityTriageAgent(model=args.model, deployment_parser=deployment_parser)

    # Create code reader function
    def code_reader(file_path: str, line_num: int) -> Optional[str]:
        return scanner.read_code_context(file_path, line_num, args.context_lines)

    # Handle JSONL streaming format differently
    if args.format == "jsonl":
        # For JSONL, we stream results as they're completed
        if not args.output:
            print("Error: JSONL format requires --output to be specified", file=sys.stderr)
            sys.exit(1)

        # Open file for writing and stream results
        with open(args.output, 'w') as f:
            async for analysis in agent.triage_all_findings_streaming(
                findings, code_reader, max_real_handlers=args.max_real_handlers
            ):
                # Write each analysis as a JSON line
                json_line = analysis.model_dump_json()
                f.write(json_line + '\n')
                f.flush()  # Ensure immediate write for streaming

        print(f"\nResults streamed to: {args.output}")
        print("(Each line is a separate JSON object - JSONL format)")
    else:
        # For other formats, use the original batch processing
        prioritized_findings = await agent.triage_all_findings(
            findings, code_reader, max_real_handlers=args.max_real_handlers
        )

        # Step 3: Output results
        print("\n" + "=" * 80)
        print("STEP 3: Generating Report")
        print("=" * 80 + "\n")

        if args.format == "json":
            output_text = prioritized_findings.model_dump_json(indent=2)
        elif args.format == "markdown":
            output_text = format_output_markdown(prioritized_findings, args)
        else:  # text
            output_text = format_output_text(prioritized_findings, args)

        # Write to file or stdout
        if args.output:
            args.output.write_text(output_text)
            print(f"Results written to: {args.output}")
        else:
            print(output_text)

    print("\n" + "=" * 80)
    print("Analysis Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
