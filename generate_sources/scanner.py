"""AST-grep scanner and result parser."""

import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import re

from models import AstGrepFinding


class AstGrepScanner:
    """Runs ast-grep scans and parses results."""

    def __init__(self, rules_dir: Path, target_dir: Path):
        """
        Initialize the scanner.

        Args:
            rules_dir: Directory containing ast-grep rule files
            target_dir: Target codebase directory to scan
        """
        self.rules_dir = rules_dir
        self.target_dir = target_dir
        self._verify_ast_grep_installed()

    def _verify_ast_grep_installed(self) -> None:
        """Check if ast-grep is installed."""
        try:
            subprocess.run(
                ["ast-grep", "--version"],
                capture_output=True,
                check=True,
                text=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "ast-grep is not installed. Install with: cargo install ast-grep"
            )

    def get_all_rules(self) -> List[Path]:
        """Get all rule files from the rules directory."""
        rule_files = list(self.rules_dir.glob("**/*.yml"))
        if not rule_files:
            raise ValueError(f"No rule files found in {self.rules_dir}")
        return rule_files

    def scan_with_rule(self, rule_file: Path) -> List[Dict]:
        """
        Run ast-grep scan with a specific rule file.

        Args:
            rule_file: Path to the rule YAML file

        Returns:
            List of findings as dictionaries
        """
        cmd = [
            "ast-grep",
            "scan",
            "-r", str(rule_file),
            "--json",
            str(self.target_dir)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # Don't raise on non-zero exit (findings present)
            )

            # ast-grep returns non-zero when findings are present
            if result.stdout:
                try:
                    # Parse JSON output
                    findings = json.loads(result.stdout)
                    return findings if isinstance(findings, list) else []
                except json.JSONDecodeError:
                    # Fallback to text parsing if JSON fails
                    return self._parse_text_output(result.stdout, rule_file)

            return []

        except Exception as e:
            print(f"Error scanning with {rule_file.name}: {e}")
            return []

    def _parse_text_output(self, output: str, rule_file: Path) -> List[Dict]:
        """
        Parse text output from ast-grep when JSON is not available.

        Args:
            output: Text output from ast-grep
            rule_file: Rule file used for scanning

        Returns:
            List of parsed findings
        """
        findings = []
        lines = output.strip().split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for file:line:col pattern
            match = re.match(r'^(.+?):(\d+):(\d+)', line)
            if match:
                file_path = match.group(1)
                line_num = int(match.group(2))
                col = int(match.group(3))

                # Next line usually contains the message
                message = ""
                code_snippet = ""

                if i + 1 < len(lines):
                    i += 1
                    msg_line = lines[i].strip()
                    if msg_line.startswith('|'):
                        code_snippet = msg_line[1:].strip()
                    else:
                        message = msg_line

                if i + 1 < len(lines) and lines[i + 1].strip().startswith('|'):
                    i += 1
                    code_snippet = lines[i][1:].strip()

                findings.append({
                    'file': file_path,
                    'line': line_num,
                    'column': col,
                    'message': message,
                    'snippet': code_snippet,
                    'rule': rule_file.stem
                })

            i += 1

        return findings

    def _extract_framework_and_language(self, rule_file: Path) -> tuple[str, str]:
        """
        Extract framework and language from rule file path.

        Args:
            rule_file: Path to the rule file

        Returns:
            Tuple of (framework_name, language)
        """
        # Rule files are in format: rules/{language}/{framework}-routes.yml
        language = rule_file.parent.name
        framework = rule_file.stem.replace('-routes', '').replace('-', ' ').title()

        return framework, language

    def parse_finding(self, raw_finding: Dict, rule_file: Path) -> AstGrepFinding:
        """
        Parse a raw ast-grep finding into structured format.

        Args:
            raw_finding: Raw finding dictionary from ast-grep
            rule_file: Rule file that generated the finding

        Returns:
            Parsed AstGrepFinding
        """
        framework, language = self._extract_framework_and_language(rule_file)

        # Handle both JSON and text parsed formats
        file_path = raw_finding.get('file', raw_finding.get('path', ''))
        line_num = raw_finding.get('line', raw_finding.get('range', {}).get('start', {}).get('line', 0))
        column = raw_finding.get('column', raw_finding.get('range', {}).get('start', {}).get('column', 0))
        message = raw_finding.get('message', '')
        snippet = raw_finding.get('snippet', raw_finding.get('text', raw_finding.get('lines', '')))
        rule_id = raw_finding.get('rule', raw_finding.get('ruleId', rule_file.stem))

        return AstGrepFinding(
            file_path=file_path,
            line_number=line_num,
            column=column,
            rule_id=rule_id,
            message=message,
            code_snippet=snippet if isinstance(snippet, str) else str(snippet),
            framework=framework,
            language=language
        )

    def _should_skip_file(self, file_path: str) -> bool:
        """
        Determine if a file should be skipped (generated, minified, etc.).

        Args:
            file_path: Path to check

        Returns:
            True if file should be skipped
        """
        # Normalize path
        path_lower = file_path.lower()

        # Skip patterns for generated/minified files
        skip_patterns = [
            '/generated/',
            '/dist/',
            '/build/',
            '/.next/',
            '/out/',
            '/__generated__/',
            '/node_modules/',
            '/vendor/',
            '/.venv/',
            '/venv/',
            '/target/',
            '.min.js',
            '.min.css',
            '-min.js',
            '.bundle.js',
            '.chunk.js',
            'webpack.',
            'rollup.',
            'parcel.',
            '.d.ts',  # TypeScript declaration files
        ]

        # Check if any skip pattern matches
        for pattern in skip_patterns:
            if pattern in path_lower:
                return True

        # Skip files with "generated" or "codegen" in the name
        filename = Path(file_path).name.lower()
        if 'generated' in filename or 'codegen' in filename:
            return True

        return False

    def scan_all(self) -> List[AstGrepFinding]:
        """
        Scan with all available rules.

        Returns:
            List of all findings from all rules
        """
        all_findings = []
        skipped_count = 0
        rule_files = self.get_all_rules()

        print(f"Found {len(rule_files)} rule files")

        for rule_file in rule_files:
            framework, language = self._extract_framework_and_language(rule_file)
            print(f"Scanning with {language}/{framework}...")

            raw_findings = self.scan_with_rule(rule_file)

            for raw_finding in raw_findings:
                try:
                    finding = self.parse_finding(raw_finding, rule_file)

                    # Skip generated/minified files
                    if self._should_skip_file(finding.file_path):
                        skipped_count += 1
                        continue

                    all_findings.append(finding)
                except Exception as e:
                    print(f"Error parsing finding from {rule_file.name}: {e}")
                    continue

        print(f"\nTotal findings: {len(all_findings)}")
        if skipped_count > 0:
            print(f"Skipped {skipped_count} findings in generated/minified files")
        return all_findings

    def read_code_context(
        self,
        file_path: str,
        line_number: int,
        context_lines: int = 20
    ) -> Optional[str]:
        """
        Read code context around a finding.

        Args:
            file_path: Path to the file
            line_number: Line number of the finding
            context_lines: Number of lines before and after to include

        Returns:
            Code snippet with context, or None if file cannot be read
        """
        try:
            full_path = self.target_dir / file_path if not Path(file_path).is_absolute() else Path(file_path)

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)

            context = ''.join(lines[start:end])
            return context

        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
