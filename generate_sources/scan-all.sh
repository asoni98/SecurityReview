#!/bin/bash

# API Route Scanner - Scan codebase for API route handlers across all supported frameworks
# Usage: ./scan-all.sh [target_directory] [output_file]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULES_DIR="$SCRIPT_DIR/rules"

# Default target is current directory
TARGET_DIR="${1:-.}"

# Output file (optional)
OUTPUT_FILE="${2:-}"

# Check if ast-grep is installed
if ! command -v ast-grep &> /dev/null; then
    echo -e "${RED}Error: ast-grep is not installed${NC}"
    echo "Install it with: cargo install ast-grep"
    exit 1
fi

# Check if rules directory exists
if [ ! -d "$RULES_DIR" ]; then
    echo -e "${RED}Error: Rules directory not found: $RULES_DIR${NC}"
    exit 1
fi

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}API Route Handler Scanner${NC}"
echo -e "${BLUE}======================================${NC}"
echo -e "Target directory: ${GREEN}$TARGET_DIR${NC}"
echo -e "Rules location: ${GREEN}$RULES_DIR${NC}"
echo ""

# Initialize output file if specified
if [ -n "$OUTPUT_FILE" ]; then
    echo "API Route Handler Scan Results" > "$OUTPUT_FILE"
    echo "Target: $TARGET_DIR" >> "$OUTPUT_FILE"
    echo "Scan date: $(date)" >> "$OUTPUT_FILE"
    echo "======================================" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo -e "Output will be saved to: ${GREEN}$OUTPUT_FILE${NC}"
    echo ""
fi

# Track total findings
TOTAL_FINDINGS=0
RULES_SCANNED=0

# Scan with each rule file in the rules directory
for LANG_DIR in "$RULES_DIR"/*; do
    if [ -d "$LANG_DIR" ]; then
        LANG_NAME=$(basename "$LANG_DIR")
        LANG_DISPLAY=$(echo "$LANG_NAME" | awk '{print toupper(substr($0,1,1)) substr($0,2)}')

        echo -e "${BLUE}Scanning $LANG_DISPLAY routes...${NC}"

        LANG_FOUND=0

        for RULE_FILE in "$LANG_DIR"/*.yml; do
            if [ -f "$RULE_FILE" ]; then
                RULES_SCANNED=$((RULES_SCANNED + 1))
                RULE_NAME=$(basename "$RULE_FILE" .yml)

                # Run ast-grep and capture output
                if OUTPUT=$(ast-grep scan -r "$RULE_FILE" "$TARGET_DIR" 2>&1); then
                    if [ -n "$OUTPUT" ]; then
                        # Count findings (ast-grep outputs file:line:col format)
                        FINDING_COUNT=$(echo "$OUTPUT" | grep -c "^" || true)
                        TOTAL_FINDINGS=$((TOTAL_FINDINGS + FINDING_COUNT))
                        LANG_FOUND=$((LANG_FOUND + FINDING_COUNT))

                        if [ -n "$OUTPUT_FILE" ]; then
                            echo "=== $LANG_DISPLAY - $RULE_NAME ===" >> "$OUTPUT_FILE"
                            echo "$OUTPUT" >> "$OUTPUT_FILE"
                            echo "" >> "$OUTPUT_FILE"
                        else
                            echo -e "${GREEN}  ✓ $RULE_NAME${NC}"
                            echo "$OUTPUT"
                            echo ""
                        fi
                    fi
                fi
            fi
        done

        if [ $LANG_FOUND -eq 0 ]; then
            echo -e "${YELLOW}  No $LANG_DISPLAY routes found${NC}"
        else
            echo -e "${GREEN}  Found $LANG_FOUND $LANG_DISPLAY route(s)${NC}"
        fi

        echo ""
    fi
done

echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Scan Complete${NC}"
echo -e "Rules scanned: ${GREEN}$RULES_SCANNED${NC}"
echo -e "Total findings: ${GREEN}$TOTAL_FINDINGS${NC}"

if [ -n "$OUTPUT_FILE" ]; then
    echo "" >> "$OUTPUT_FILE"
    echo "======================================" >> "$OUTPUT_FILE"
    echo "Rules scanned: $RULES_SCANNED" >> "$OUTPUT_FILE"
    echo "Total findings: $TOTAL_FINDINGS" >> "$OUTPUT_FILE"
    echo -e "Results saved to: ${GREEN}$OUTPUT_FILE${NC}"
fi

echo -e "${BLUE}======================================${NC}"

# Exit with error if no rules were found
if [ $RULES_SCANNED -eq 0 ]; then
    echo -e "${RED}Error: No rule files found in $RULES_DIR${NC}"
    exit 1
fi
