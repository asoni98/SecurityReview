# AI Security Analysis Agent

An intelligent security analysis tool that uses AI to analyze user input handlers identified by ast-grep and prioritize them for security code review.

## Overview

This tool combines static analysis (ast-grep) with AI-powered analysis (pydantic-ai) to:

1. **Scan** - Use ast-grep rules to find all user input entry points across multiple frameworks
2. **Analyze** - Use LLM to analyze each function for security risks, input sources, and vulnerabilities
3. **Prioritize** - Generate a risk-sorted list with detailed reasoning to guide security reviewers

## Features

- **Multi-Framework Support** - Analyzes 29+ web frameworks across 7 languages (JavaScript/TypeScript, Python, Java, Go, Rust, Ruby, C++)
- **AI-Powered Analysis** - Uses GPT-4, Claude, or other LLMs to understand code context and identify security risks
- **Risk Prioritization** - Automatically sorts findings by severity (CRITICAL → HIGH → MEDIUM → LOW → INFO)
- **Security Focus** - Specifically looks for:
  - Unauthenticated input handlers
  - Missing input validation/sanitization
  - Potential injection vulnerabilities (SQL, XSS, Command, etc.)
  - Authorization bypasses
  - Insecure deserialization
  - Business logic flaws
- **Structured Output** - JSON, Markdown, or formatted text reports
- **Actionable Insights** - Provides reasoning, confidence scores, and specific vulnerability types

## Installation

### Prerequisites

1. **Python 3.10+**
2. **ast-grep** - Install via:
   ```bash
   # Using Cargo (Rust)
   cargo install ast-grep

   # Using Homebrew (macOS)
   brew install ast-grep

   # Using npm
   npm install -g @ast-grep/cli
   ```

### Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set your API key (choose one based on your model)
export OPENAI_API_KEY="your-openai-key"
# OR
export ANTHROPIC_API_KEY="your-anthropic-key"

# Make the script executable (optional)
chmod +x analyze.py
```

## Quick Start

```bash
# Analyze current directory with GPT-4
python analyze.py --target . --model openai:gpt-4o

# Analyze specific project with Claude
python analyze.py --target /path/to/project --model anthropic:claude-3-5-sonnet-20241022

# Save results to file
python analyze.py --target . --output security-report.json --format json

# Show only high-risk findings
python analyze.py --target . --min-risk high
```

## Usage

### Basic Command

```bash
python analyze.py [OPTIONS]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--target PATH` | Target codebase directory | Current directory |
| `--rules PATH` | Directory with ast-grep rules | `./rules` |
| `--model MODEL` | AI model to use | `openai:gpt-4o` |
| `--output FILE` | Output file path (required for jsonl format) | stdout |
| `--format FORMAT` | Output format: json, jsonl, markdown, text | `text` |
| `--min-risk LEVEL` | Minimum risk level: critical, high, medium, low, info | `info` |
| `--max-findings N` | Limit number of findings to analyze | All |
| `--context-lines N` | Lines of code context to analyze | 30 |
| `--max-real-handlers N` | Stop after finding N real handlers | All |
| `--deployment-model PATH` | Deployment model markdown file for context enrichment | None |

### Supported Models

**OpenAI**:
- `openai:gpt-4o` (recommended)
- `openai:gpt-4o-mini`
- `openai:gpt-4-turbo`

**Anthropic**:
- `anthropic:claude-3-5-sonnet-20241022` (recommended)
- `anthropic:claude-3-5-haiku-20241022`
- `anthropic:claude-3-opus-20240229`

**Others** (if you have pydantic-ai providers installed):
- `groq:mixtral-8x7b-32768`
- `mistral:mistral-large-latest`

## Examples

### Example 1: Analyze Node.js API

```bash
python analyze.py \
  --target /path/to/nodejs-api \
  --model openai:gpt-4o \
  --format markdown \
  --output api-security-review.md
```

### Example 2: Quick Scan for Critical Issues

```bash
python analyze.py \
  --target . \
  --min-risk critical \
  --max-findings 10
```

### Example 3: Full Analysis with JSON Output

```bash
python analyze.py \
  --target /path/to/microservices \
  --model anthropic:claude-3-5-sonnet-20241022 \
  --format json \
  --output full-analysis.json \
  --context-lines 50
```

### Example 4: Streaming Analysis with Deployment Context

```bash
# Stream findings with infrastructure context enrichment
python analyze.py \
  --target /path/to/codebase \
  --deployment-model deployment_model.json \
  --format jsonl \
  --output enriched-sources.jsonl \
  --model openai:gpt-5

# The next agent can start processing immediately:
tail -f enriched-sources.jsonl | while read line; do
  # Each finding now includes deployment context
  echo "$line" | jq '.deployment_context.service_name, .risk_level'
done
```

## Deployment Model Enrichment

Enrich security findings with infrastructure and deployment context by providing a deployment model JSON file:

```bash
python analyze.py \
  --target /path/to/codebase \
  --deployment-model deployment_model.json \
  --format jsonl \
  --output enriched-findings.jsonl
```

### What Gets Enriched

When you provide a deployment model file, each finding is enriched with:
- **Service Name**: Which service/component the code belongs to
- **Trust Zone**: Public Zone, Application Zone, or Data Zone
- **Network Exposure**: Internet-facing vs Internal only
- **Deployment Target**: ECS Fargate, Lambda, EC2, etc.
- **Authentication Method**: OAuth2 JWT, IAM Role, mTLS, etc.
- **Service Dependencies**: What calls this service (upstream) and what it calls (downstream)

### Deployment Model Format

The deployment model should be a JSON file generated by the `deployment_understanding` phase. The JSON schema includes:

- **services**: Map of service names to service details (type, purpose, runtime, deployment target, network exposure, repository paths)
- **trust_zones**: Array of security zones with services in each zone
- **communications**: Service-to-service communication patterns with auth methods
- **internet_facing_endpoints**: List of publicly accessible services

Generate this file using:
```bash
cd deployment_understanding
npm start /path/to/codebase /path/to/iac deployment_model.json
```

### Benefits

1. **Better Risk Assessment**: LLM considers deployment context when assigning risk levels
2. **Infrastructure-Aware Analysis**: Internet-facing services are automatically flagged as higher risk
3. **Complete Context**: Next phase agents get both code analysis and deployment information
4. **Compliance**: Helps map findings to security zones for compliance reporting

### Example Enriched Output

```json
{
  "function_name": "upload_image",
  "location": {"file_path": "app/images/upload.py", "line_number": 45},
  "risk_level": "critical",
  "deployment_context": {
    "service_name": "yoctogram-api",
    "trust_zone": "Public Zone",
    "network_exposure": "Internet-facing",
    "deployment_target": "ECS Fargate (single container task behind ALB)",
    "authentication_method": "OAuth2 JWT",
    "upstream_services": ["External clients"],
    "downstream_services": ["Aurora PostgreSQL", "AWS S3 Bucket"]
  }
}
```

## Streaming Output with JSONL

For large codebases or when you want to pipeline results to another agent, use the **JSONL (JSON Lines)** format:

```bash
python analyze.py \
  --target /path/to/codebase \
  --format jsonl \
  --output findings.jsonl
```

### Benefits of JSONL Format

1. **Streaming**: Each finding is written to the file immediately after analysis, not at the end
2. **Pipelining**: The next agent can start processing findings while analysis is still running
3. **Memory Efficient**: No need to hold all findings in memory
4. **Interruptible**: If interrupted, you still have partial results

### JSONL Output Format

Each line is a complete JSON object representing a `FunctionAnalysis`:

```jsonl
{"function_name":"handleUpload","location":{"file_path":"src/api/upload.js","line_number":45},"framework":"Express","language":"javascript","risk_level":"critical",...}
{"function_name":"getUser","location":{"file_path":"src/api/users.js","line_number":12},"framework":"Express","language":"javascript","risk_level":"high",...}
{"function_name":"createPost","location":{"file_path":"src/api/posts.js","line_number":89},"framework":"Express","language":"javascript","risk_level":"medium",...}
```

### Reading JSONL Output

Process findings as they're written:

```bash
# In one terminal: run analysis (streaming)
python analyze.py --target . --format jsonl --output findings.jsonl

# In another terminal: process findings in real-time
tail -f findings.jsonl | while read line; do
  echo "New finding: $(echo $line | jq -r '.function_name')"
done
```

Load in Python:

```python
import json

findings = []
with open('findings.jsonl', 'r') as f:
    for line in f:
        finding = json.loads(line)
        findings.append(finding)
        # Or process immediately:
        if finding['risk_level'] in ['critical', 'high']:
            print(f"High-risk finding: {finding['function_name']}")
```

### Pipeline with Next Agent

```bash
# Start analysis in streaming mode with deployment enrichment
python analyze.py \
  --target . \
  --deployment-model deployment_model.json \
  --format jsonl \
  --output sources.jsonl &

# As findings are written, process them with another agent
tail -f sources.jsonl | while read line; do
  # Extract finding details - now includes deployment context
  echo "$line" | python next_agent.py
done
```

### Combined Example: Full Pipeline

```bash
# 1. Generate deployment model
cd deployment_understanding
npm start ../yoctogram ../yoctogram/infrastructure deployment_model.json
cd ..

# 2. Run streaming analysis with deployment enrichment
python analyze.py \
  --target ../yoctogram \
  --deployment-model deployment_understanding/deployment_model.json \
  --format jsonl \
  --output findings.jsonl \
  --model openai:gpt-5 \
  --max-real-handlers 50

# 3. Each line in findings.jsonl contains:
#    - Code analysis (function, risk level, security concerns)
#    - Deployment context (service, trust zone, network exposure)
#    - Ready for the next security review agent to process
```

## Output Format

### Text Output

```
================================================================================
SECURITY ANALYSIS REPORT - USER INPUT HANDLERS
================================================================================

EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
[AI-generated executive summary highlighting critical findings]

STATISTICS
--------------------------------------------------------------------------------
Total Functions Analyzed: 47
High Priority (CRITICAL + HIGH): 12

Risk Level Breakdown:
  CRITICAL: 3
  HIGH    : 9
  MEDIUM  : 18
  LOW     : 15
  INFO    : 2

RECOMMENDATIONS
--------------------------------------------------------------------------------
1. [AI-generated recommendation 1]
2. [AI-generated recommendation 2]
...

DETAILED FINDINGS
================================================================================

[1] CRITICAL - handleUserUpload
--------------------------------------------------------------------------------
Location: src/api/upload.js:45
Framework: Express (javascript)
Endpoint: POST /api/upload
Unauthenticated Input: YES
Input Sources: http_body, file_upload

Security Assessment:
  Concerns:
    - [path_traversal] User-supplied filename not validated (85% confidence)
    - [command_injection] Filename used in shell command (90% confidence)

  Security Controls:
    Input Validation: Missing
    Sanitization: Missing
    Authorization: Missing

Reasoning:
  This function accepts file uploads from unauthenticated users and uses
  the user-supplied filename directly in a shell command without validation.
  This is a critical path traversal and command injection vulnerability.
  [more detailed analysis...]
```

### JSON Output

```json
{
  "total_functions_analyzed": 47,
  "high_priority_count": 12,
  "summary": "...",
  "recommendations": ["...", "..."],
  "findings": [
    {
      "function_name": "handleUserUpload",
      "location": {
        "file_path": "src/api/upload.js",
        "line_number": 45
      },
      "framework": "Express",
      "language": "javascript",
      "risk_level": "critical",
      "accepts_unauthenticated_input": true,
      "input_sources": ["http_body", "file_upload"],
      "security_concerns": [
        {
          "vulnerability_type": "path_traversal",
          "description": "User-supplied filename not validated",
          "confidence": 0.85
        }
      ],
      "has_input_validation": false,
      "has_sanitization": false,
      "has_authorization_check": false,
      "reasoning": "..."
    }
  ]
}
```

### Markdown Output

Formatted markdown with:
- Executive summary
- Statistics and charts
- Risk-level badges (🔴 CRITICAL, 🟠 HIGH, etc.)
- Collapsible sections
- Code references with line numbers

## How It Works

### Step 1: Static Analysis (ast-grep)

The tool scans your codebase using ast-grep rules to find:
- HTTP route handlers (Express, FastAPI, Spring Boot, etc.)
- GraphQL resolvers
- gRPC service methods
- WebSocket handlers
- Any function that accepts user input

### Step 2: AI Analysis

For each finding, the agent:
1. Reads surrounding code context (default: 30 lines)
2. Sends to LLM with security-focused prompts
3. Analyzes for:
   - Input sources (body, headers, params, etc.)
   - Authentication requirements
   - Security controls (validation, sanitization, authorization)
   - Potential vulnerabilities
   - Risk level

### Step 3: Prioritization

The agent:
1. Sorts findings by risk level
2. Generates executive summary
3. Provides actionable recommendations
4. Outputs in requested format

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     analyze.py (CLI)                         │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴──────────────┐
            │                              │
            ▼                              ▼
┌──────────────────────┐      ┌──────────────────────┐
│  scanner.py          │      │  agent.py            │
│                      │      │                      │
│  - AstGrepScanner    │      │  - SecurityAgent     │
│  - Run ast-grep      │──────│  - LLM analysis      │
│  - Parse findings    │      │  - Prioritization    │
└──────────────────────┘      └──────────────────────┘
            │                              │
            ▼                              ▼
┌──────────────────────┐      ┌──────────────────────┐
│  models.py           │      │  Output Formatters   │
│                      │      │                      │
│  - FunctionAnalysis  │      │  - JSON              │
│  - SecurityConcern   │      │  - Markdown          │
│  - RiskLevel         │      │  - Text              │
└──────────────────────┘      └──────────────────────┘
```

## Configuration

### Custom Rules

To add support for additional frameworks:

1. Create a new rule file in `rules/{language}/{framework}-routes.yml`
2. Follow the ast-grep YAML format
3. Run the analyzer - it will automatically pick up new rules

### Custom Prompts

Edit `agent.py` to customize the system prompts:

- `SECURITY_ANALYSIS_SYSTEM_PROMPT` - Controls how individual functions are analyzed
- Summary agent prompt - Controls executive summary generation

## Performance

- **ast-grep scanning**: Fast (~1-5 seconds for large codebases)
- **AI analysis**: Depends on findings count and model
  - GPT-4: ~3-5 seconds per finding
  - Claude Sonnet: ~2-4 seconds per finding
  - For 50 findings: ~3-5 minutes total

**Tip**: Use `--max-findings` to test on a subset first

## Cost Estimation

Approximate costs per finding (based on ~1000 tokens input, ~500 tokens output):

| Model | Cost per Finding | Cost for 100 Findings |
|-------|------------------|----------------------|
| GPT-4o | ~$0.01 | ~$1.00 |
| GPT-4o-mini | ~$0.001 | ~$0.10 |
| Claude 3.5 Sonnet | ~$0.01 | ~$1.00 |
| Claude 3.5 Haiku | ~$0.001 | ~$0.10 |

## Limitations

- **Static Analysis**: Cannot detect runtime-only vulnerabilities
- **Context Window**: Limited to configured context lines (default 30)
- **LLM Accuracy**: AI analysis may have false positives/negatives
- **Framework Coverage**: Only detects patterns covered by ast-grep rules
- **Code Understanding**: Complex abstractions may not be fully understood

## Best Practices

1. **Start Small**: Use `--max-findings` to test on a subset first
2. **Review High-Risk First**: Use `--min-risk high` to focus on critical issues
3. **Provide Context**: Increase `--context-lines` for complex code (but watch costs)
4. **Iterate**: Use findings to improve your codebase, then re-scan
5. **Combine with Other Tools**: Use alongside SAST, DAST, and manual reviews
6. **Human Review Required**: Always have a human security expert review AI findings

## Troubleshooting

### "ast-grep is not installed"

Install ast-grep:
```bash
cargo install ast-grep
# OR
brew install ast-grep
```

### "No rule files found"

Ensure the `rules/` directory exists and contains `.yml` files.

### "API key not found"

Set your API key:
```bash
export OPENAI_API_KEY="your-key"
# OR
export ANTHROPIC_API_KEY="your-key"
```

### "Rate limit exceeded"

Reduce concurrency or add delays between requests. Consider using `--max-findings` to analyze in batches.

### "Out of memory"

Reduce `--context-lines` or analyze fewer findings at once with `--max-findings`.

## Contributing

To improve the agent:

1. **Add more ast-grep rules** for additional frameworks
2. **Improve prompts** in `agent.py` for better analysis
3. **Add new output formats** in `analyze.py`
4. **Enhance models** in `models.py` with additional fields

## Security Note

This tool is designed to **help** security reviewers, not replace them. Always:
- Have experienced security professionals review findings
- Validate AI-identified vulnerabilities manually
- Use multiple security tools in combination
- Conduct thorough penetration testing

## License

See main repository license.

## Related Tools

- **ast-grep**: https://ast-grep.github.io/
- **pydantic-ai**: https://ai.pydantic.dev/
- **Semgrep**: https://semgrep.dev/
- **CodeQL**: https://codeql.github.com/
