"""Pydantic-AI agent for security analysis of user input handlers."""

from typing import List

from pydantic_ai import Agent

from models import (
    FunctionAnalysis,
    PrioritizedFindings,
    AstGrepFinding,
    RiskLevel,
)


# Fast false positive detection prompt
FAST_FALSE_POSITIVE_CHECK = """You are a fast filter that quickly identifies obvious false positives.

Given this code snippet, answer ONE question: Is this a real user input handler (API endpoint, GraphQL resolver, gRPC handler) that processes runtime requests?

Answer with ONLY:
- "REAL" if it's an actual handler that processes user requests at runtime
- "FALSE_POSITIVE" if it's any of: config files, test code, type declarations, utility functions, client-side code, build scripts

Be VERY strict - when in doubt, say REAL (we'll do detailed analysis later)."""

# System prompt for the triage agent
USER_INPUT_TRIAGE_SYSTEM_PROMPT = """You are a security triage specialist identifying which functions handle untrusted user input and should be prioritized for deep security review.

Your job is NOT to find vulnerabilities - that comes later. Your job is to:

1. **Determine if this is actually a user input handler**:
   - Is this a real API endpoint, GraphQL resolver, gRPC handler, or other entry point?
   - Or is this just configuration, test code, or a false positive from the scanner?
   - If it's NOT a real user input handler, mark it as INFO risk with clear reasoning

2. **Identify what user input it handles**:
   - HTTP request body, headers, query params, path params?
   - GraphQL arguments?
   - gRPC request messages?
   - File uploads?
   - WebSocket messages?

3. **Assess authentication requirements**:
   - Does this endpoint require authentication? (look for auth middleware, decorators, checks)
   - Can unauthenticated users reach this code?
   - This is CRITICAL for prioritization

4. **Identify what the function does with user input**:
   - Database queries (SQL, NoSQL)
   - File system operations
   - External API calls
   - Command execution
   - Template rendering
   - Business logic operations
   - Simple data retrieval

5. **Assign triage priority** (CRITICAL > HIGH > MEDIUM > LOW > INFO):
   - **CRITICAL**: Unauthenticated + handles sensitive operations (DB writes, file system, commands, etc.)
   - **HIGH**: Authenticated but handles sensitive operations, OR unauthenticated read-only with complex logic
   - **MEDIUM**: Authenticated + standard CRUD operations
   - **LOW**: Simple authenticated read operations
   - **INFO**: Not a real user input handler (config, tests, etc.)

6. **Provide context for the next reviewer**:
   - What specific user inputs should they examine?
   - What operations should they scrutinize?
   - Why is this function prioritized at this level?

Be precise and concise. The next agent will do the deep vulnerability analysis - you're just triaging and prioritizing."""


class SecurityTriageAgent:
    """AI agent for triaging and prioritizing user input handlers for security review."""

    def __init__(self, model: str = "openai:gpt-5", api_key: str | None = None):
        """
        Initialize the security triage agent.

        Args:
            model: Model identifier (e.g., "openai:gpt-5", "anthropic:claude-3-5-sonnet-20241022")
            api_key: API key for the model provider
        """
        self.model_name = model

        # Fast filter agent for quick false positive detection (uses cheaper/faster model)
        fast_model = "openai:gpt-5-mini" if "openai" in model else model
        self.fast_filter = Agent(
            fast_model,
            output_type=str,
            system_prompt=FAST_FALSE_POSITIVE_CHECK,
        )

        # Initialize the triage agent for individual function analysis
        self.triage_agent = Agent(
            model,
            output_type=FunctionAnalysis,
            system_prompt=USER_INPUT_TRIAGE_SYSTEM_PROMPT,
        )

        # Agent for creating the final prioritized summary
        self.summary_agent = Agent(
            model,
            output_type=PrioritizedFindings,
            system_prompt="""You are a security lead creating a prioritized triage report for the security review team.

Your output should:
1. Summarize how many real user input handlers were found vs false positives
2. Highlight the highest priority items that need immediate deep security review
3. Provide guidance on what the security reviewers should focus on for each priority level
4. Recommend an order of review (which functions to analyze first)

This is a TRIAGE report - the actual vulnerability hunting happens in the next phase.""",
        )

    async def triage_function(
        self, finding: AstGrepFinding, code_context: str
    ) -> FunctionAnalysis:
        """
        Triage a single function to determine if it handles user input and its priority.

        Args:
            finding: The ast-grep finding
            code_context: Full code context around the finding

        Returns:
            Triage analysis with priority and context for next reviewer
        """
        triage_prompt = f"""Triage this potential user input handler found by ast-grep:

**Location**: {finding.file_path}:{finding.line_number}
**Framework**: {finding.framework}
**Language**: {finding.language}
**Rule that matched**: {finding.rule_id}

**Code Context**:
```{finding.language}
{code_context}
```

**Your task**: Determine if this is a real user input handler that needs security review, and assign the appropriate triage priority.

Answer these questions:
1. Is this actually a user input handler (API endpoint, GraphQL resolver, etc.) or is it configuration/test code?
2. What user input does it accept? (HTTP body, headers, URL params, GraphQL args, etc.)
3. Does it require authentication? Look for auth middleware, decorators, or checks
4. What does it DO with user input? (DB queries, file operations, external calls, business logic, etc.)
5. What priority level for security review? (CRITICAL/HIGH/MEDIUM/LOW/INFO)
6. What should the next security reviewer focus on when analyzing this function?

Extract the function/handler name, endpoint path, HTTP methods if visible.

Provide clear, actionable reasoning for your triage decision."""

        result = await self.triage_agent.run(triage_prompt)
        return result.output

    async def prioritize_findings(
        self, analyses: List[FunctionAnalysis]
    ) -> PrioritizedFindings:
        """
        Create a prioritized summary of all findings.

        Args:
            analyses: List of individual function analyses

        Returns:
            Prioritized and summarized findings
        """
        # Sort by risk level
        risk_order = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 3,
            RiskLevel.INFO: 4,
        }
        sorted_analyses = sorted(analyses, key=lambda x: risk_order[x.risk_level])

        high_priority_count = sum(
            1 for a in analyses if a.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        )

        # Count real user input handlers vs false positives
        real_handlers = [a for a in analyses if a.risk_level != RiskLevel.INFO]
        false_positives = [a for a in analyses if a.risk_level == RiskLevel.INFO]

        summary_prompt = f"""Create a triage summary for the security review team.

**Total Items Scanned**: {len(analyses)}
**Real User Input Handlers**: {len(real_handlers)}
**False Positives (config/tests)**: {len(false_positives)}
**High Priority for Review**: {high_priority_count} (CRITICAL + HIGH)

**Triage Breakdown**:
- CRITICAL: {sum(1 for a in analyses if a.risk_level == RiskLevel.CRITICAL)} (unauthenticated + sensitive operations)
- HIGH: {sum(1 for a in analyses if a.risk_level == RiskLevel.HIGH)} (authenticated sensitive ops OR unauth complex)
- MEDIUM: {sum(1 for a in analyses if a.risk_level == RiskLevel.MEDIUM)} (authenticated standard CRUD)
- LOW: {sum(1 for a in analyses if a.risk_level == RiskLevel.LOW)} (simple authenticated reads)
- INFO: {sum(1 for a in analyses if a.risk_level == RiskLevel.INFO)} (not real user input handlers)

**Top Priority Functions for Deep Review**:
{self._format_top_concerns(sorted_analyses[:10])}

Create:
1. A summary (2-3 paragraphs) explaining the triage results and what was found
2. Specific guidance on what to review first and what to focus on
3. 3-5 recommendations for the security review process

Remember: This is TRIAGE only - vulnerability identification comes in the next phase."""

        result = await self.summary_agent.run(summary_prompt)

        # Override the findings with our sorted list
        return PrioritizedFindings(
            total_functions_analyzed=len(analyses),
            high_priority_count=high_priority_count,
            findings=sorted_analyses,
            summary=result.output.summary,
            recommendations=result.output.recommendations,
        )

    def _format_top_concerns(self, top_analyses: List[FunctionAnalysis]) -> str:
        """Format top concerns for the summary prompt."""
        concerns = []
        for i, analysis in enumerate(top_analyses, 1):
            concern_types = [
                c.vulnerability_type.value for c in analysis.security_concerns
            ]
            concerns.append(
                f"{i}. {analysis.function_name} ({analysis.location.file_path}:{analysis.location.line_number})\n"
                f"   Risk: {analysis.risk_level.value.upper()}\n"
                f"   Concerns: {', '.join(concern_types) if concern_types else 'None specific'}\n"
                f"   Auth Required: {'No' if analysis.accepts_unauthenticated_input else 'Yes'}"
            )
        return "\n".join(concerns)

    async def fast_check_false_positive(
        self, finding: AstGrepFinding, code_context: str
    ) -> bool:
        """
        Quick check if this is an obvious false positive using a fast/cheap model.

        Args:
            finding: The ast-grep finding
            code_context: Code snippet

        Returns:
            True if it's a false positive
        """
        quick_prompt = f"""File: {finding.file_path}
Framework: {finding.framework}

Code:
```{finding.language}
{code_context[:500]}
```

Is this a REAL user input handler or FALSE_POSITIVE?"""

        try:
            result = await self.fast_filter.run(quick_prompt)
            response = result.output.strip().upper()
            return "FALSE_POSITIVE" in response or "FALSE" in response
        except Exception:
            # If fast check fails, assume it's real (will do full analysis)
            return False

    async def triage_all_findings_streaming(
        self,
        findings: List[AstGrepFinding],
        code_reader: callable,
        max_real_handlers: int | None = None,
    ):
        """
        Triage findings and yield each analysis as it's completed (for streaming).

        Args:
            findings: List of ast-grep findings
            code_reader: Function to read code context (file_path, line_num) -> str
            max_real_handlers: Stop after finding this many real handlers (None = no limit)

        Yields:
            FunctionAnalysis objects as they're completed
        """
        print(f"\nTriaging {len(findings)} potential user input handlers (streaming mode)...\n")

        real_handler_count = 0
        fast_filtered_count = 0
        total_analyzed = 0

        for i, finding in enumerate(findings, 1):
            # Check if we've hit the quota for real handlers
            if max_real_handlers and real_handler_count >= max_real_handlers:
                print(
                    f"\nReached quota of {max_real_handlers} real handlers. Stopping analysis."
                )
                break

            # Simplified progress indicator
            progress = f"[{i}/{len(findings)}]"

            # Show what file is being scanned
            print(
                f"{progress} Scanning {finding.file_path}:{finding.line_number}...",
                end=" ",
                flush=True,
            )

            # Get code context
            code_context = code_reader(finding.file_path, finding.line_number)
            if not code_context:
                print("⚠ Could not read code context, skipping")
                continue

            try:
                # Fast filter check first (using cheap model)
                is_false_positive = await self.fast_check_false_positive(
                    finding, code_context
                )

                if is_false_positive:
                    fast_filtered_count += 1
                    print("○ False positive (fast filter)")
                    continue  # Skip full analysis

                # If it passed fast filter, do full analysis with GPT-5
                analysis = await self.triage_function(finding, code_context)
                total_analyzed += 1

                # Show result on same line
                if analysis.risk_level != RiskLevel.INFO:
                    real_handler_count += 1
                    print(
                        f"✓ {analysis.risk_level.value.upper()}: {analysis.function_name}"
                    )
                else:
                    print("○ False positive (detailed)")

                # Yield the analysis immediately for streaming
                yield analysis

            except Exception as e:
                print(f"✗ Error: {e}")
                continue

        # Print final summary
        print(f"\n{'='*60}")
        print(f"Streaming Analysis Complete:")
        print(f"  Total scanned: {i} files")
        print(f"  Fast filtered (cheap): {fast_filtered_count}")
        print(f"  Deep analyzed (GPT-5): {total_analyzed}")
        print(f"  Real handlers found: {real_handler_count}")
        print(f"{'='*60}\n")

    async def triage_all_findings(
        self,
        findings: List[AstGrepFinding],
        code_reader: callable,
        max_real_handlers: int | None = None,
    ) -> PrioritizedFindings:
        """
        Triage all findings and create prioritized review list.

        Args:
            findings: List of ast-grep findings
            code_reader: Function to read code context (file_path, line_num) -> str
            max_real_handlers: Stop after finding this many real handlers (None = no limit)

        Returns:
            Complete prioritized triage report
        """
        print(f"\nTriaging {len(findings)} potential user input handlers...\n")

        analyses = []
        real_handler_count = 0
        fast_filtered_count = 0

        for i, finding in enumerate(findings, 1):
            # Check if we've hit the quota for real handlers
            if max_real_handlers and real_handler_count >= max_real_handlers:
                print(
                    f"\nReached quota of {max_real_handlers} real handlers. Stopping analysis."
                )
                break

            # Simplified progress indicator
            progress = f"[{i}/{len(findings)}]"

            # Show what file is being scanned
            print(
                f"{progress} Scanning {finding.file_path}:{finding.line_number}...",
                end=" ",
                flush=True,
            )

            # Get code context
            code_context = code_reader(finding.file_path, finding.line_number)
            if not code_context:
                print("⚠ Could not read code context, skipping")
                continue

            try:
                # Fast filter check first (using cheap model)
                is_false_positive = await self.fast_check_false_positive(
                    finding, code_context
                )

                if is_false_positive:
                    fast_filtered_count += 1
                    print("○ False positive (fast filter)")
                    continue  # Skip full analysis

                # If it passed fast filter, do full analysis with GPT-5
                analysis = await self.triage_function(finding, code_context)
                analyses.append(analysis)

                # Show result on same line
                if analysis.risk_level != RiskLevel.INFO:
                    real_handler_count += 1
                    print(
                        f"✓ {analysis.risk_level.value.upper()}: {analysis.function_name}"
                    )
                else:
                    print("○ False positive (detailed)")

            except Exception as e:
                print(f"✗ Error: {e}")
                continue

        # Print summary
        real_handlers = [a for a in analyses if a.risk_level != RiskLevel.INFO]
        false_positives = [a for a in analyses if a.risk_level == RiskLevel.INFO]

        print(f"\n{'='*60}")
        print(f"Triage Summary:")
        print(f"  Total scanned: {i} files")
        print(f"  Fast filtered (cheap): {fast_filtered_count}")
        print(f"  Deep analyzed (GPT-5): {len(analyses)}")
        print(f"  Real handlers found: {len(real_handlers)}")
        print(f"  False positives (detailed): {len(false_positives)}")
        if real_handlers:
            risk_breakdown = {}
            for a in real_handlers:
                risk_breakdown[a.risk_level] = risk_breakdown.get(a.risk_level, 0) + 1
            print(f"  Risk breakdown:")
            for risk in [
                RiskLevel.CRITICAL,
                RiskLevel.HIGH,
                RiskLevel.MEDIUM,
                RiskLevel.LOW,
            ]:
                if risk in risk_breakdown:
                    print(f"    {risk.value.upper()}: {risk_breakdown[risk]}")
        print(f"{'='*60}\n")

        print("Creating prioritized triage report...")
        prioritized = await self.prioritize_findings(analyses)

        return prioritized
