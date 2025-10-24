# API Route Handler Detection Rules

Comprehensive ast-grep rules for identifying API route handlers across popular web frameworks in enterprise codebases. These rules help identify entry points for security reviews, vulnerability scanning, and code analysis.

## Quick Start

```bash
# Scan entire codebase with all rules
./scan-all.sh /path/to/codebase

# Scan and save results to file
./scan-all.sh /path/to/codebase results.txt

# Scan with specific language rules
ast-grep scan -r rules/javascript/express-routes.yml /path/to/codebase
ast-grep scan -r rules/python/fastapi-routes.yml /path/to/codebase
ast-grep scan -r rules/rust/axum-routes.yml /path/to/codebase
```

## Directory Structure

```
generate_sources/
├── README.md          # This file
├── scan-all.sh        # Automated scanning script
└── rules/             # ast-grep rule definitions
    ├── cpp/           # C++ web frameworks
    ├── go/            # Go web frameworks
    ├── java/          # Java web frameworks
    ├── javascript/    # JavaScript/TypeScript frameworks
    ├── python/        # Python web frameworks
    ├── ruby/          # Ruby web frameworks
    └── rust/          # Rust web frameworks
```

## Supported Frameworks

### JavaScript/TypeScript (8 frameworks)
- **Express.js** (`express-routes.yml`) - Traditional Node.js web framework
- **Fastify** (`fastify-routes.yml`) - High-performance web framework
- **Koa** (`koa-routes.yml`) - Modern middleware-based framework
- **NestJS** (`nestjs-routes.yml`) - Enterprise Angular-style framework with decorators
- **Next.js** (`nextjs-routes.yml`) - React framework with API routes and App Router
- **tRPC** (`trpc-routes.yml`) - Type-safe RPC framework
- **Hono** (`hono-routes.yml`) - Lightweight edge-compatible framework
- **Apollo GraphQL** (`apollo-graphql-routes.yml`) - GraphQL server implementation

### Python (4 frameworks)
- **Flask** (`flask-routes.yml`) - Micro web framework with decorators
- **FastAPI** (`fastapi-routes.yml`) - Modern async API framework
- **Django** (`django-routes.yml`) - Full-stack framework with URL patterns and class-based views
- **gRPC Python** (`grpc-python.yml`) - Google RPC framework

### Java (3 frameworks)
- **Spring Boot** (`spring-boot-routes.yml`) - Enterprise framework with @RequestMapping, @GetMapping, etc.
- **JAX-RS** (`jaxrs-routes.yml`) - Java API for RESTful Web Services
- **gRPC Java** (`grpc-java.yml`) - Google RPC framework and GraphQL (Netflix DGS)

### Go (4 frameworks)
- **net/http** (`standard-http.yml`) - Standard library HTTP handlers
- **Gin** (`gin-routes.yml`) - High-performance HTTP framework
- **Echo** (`echo-routes.yml`) - Minimalist web framework
- **gRPC Go** (`grpc-go.yml`) - Google RPC framework

### Rust (4 frameworks)
- **Actix-web** (`actix-web-routes.yml`) - Powerful actor-based framework
- **Rocket** (`rocket-routes.yml`) - Type-safe web framework
- **Axum** (`axum-routes.yml`) - Ergonomic framework built on Tower
- **tonic** (`tonic-grpc.yml`) - gRPC framework

### Ruby (2 frameworks)
- **Rails** (`rails-routes.yml`) - Full-stack MVC framework
- **Sinatra** (`sinatra-routes.yml`) - DSL for web applications

### C++ (4 frameworks)
- **Crow** (`crow-routes.yml`) - Fast and easy to use micro web framework
- **Drogon** (`drogon-routes.yml`) - High-performance HTTP framework
- **Oat++** (`oatpp-routes.yml`) - Modern web framework
- **gRPC C++** (`grpc-cpp.yml`) - Google RPC framework

## Usage

### Basic Scanning

Scan a single file or directory with a specific rule:

```bash
# Scan JavaScript/TypeScript files for Express routes
ast-grep scan -r rules/javascript/express-routes.yml /path/to/project

# Scan Python files for FastAPI routes
ast-grep scan -r rules/python/fastapi-routes.yml /path/to/project

# Scan Go files for Gin routes
ast-grep scan -r rules/go/gin-routes.yml /path/to/project
```

### Scan All Languages

Use the provided script to scan with all rules:

```bash
# Scan current directory
./scan-all.sh

# Scan specific directory
./scan-all.sh /path/to/codebase

# Save results to file
./scan-all.sh /path/to/codebase output.txt
```

### Scan Multiple Framework Rules

```bash
# Scan all JavaScript framework rules
for rule in rules/javascript/*.yml; do
  ast-grep scan -r "$rule" /path/to/project
done

# Scan all Python framework rules
for rule in rules/python/*.yml; do
  ast-grep scan -r "$rule" /path/to/project
done
```

### JSON Output

Get structured JSON output for programmatic processing:

```bash
ast-grep scan -r rules/javascript/express-routes.yml /path/to/project --json
```

## Installation

### Install ast-grep

```bash
# Using cargo (Rust package manager)
cargo install ast-grep

# Using Homebrew (macOS)
brew install ast-grep

# Using npm
npm install -g @ast-grep/cli
```

### Make scan script executable

```bash
chmod +x scan-all.sh
```

## Integration Examples

### GitHub Actions

```yaml
name: Scan API Routes
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install ast-grep
        run: cargo install ast-grep
      - name: Scan routes
        run: ./generate_sources/scan-all.sh . scan-results.txt
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: route-scan-results
          path: scan-results.txt
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Get changed files
CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

# Scan changed JavaScript/TypeScript files
if echo "$CHANGED_FILES" | grep -q "\\.js$\|\\.ts$"; then
    echo "Scanning JavaScript/TypeScript files for route handlers..."
    for rule in generate_sources/rules/javascript/*.yml; do
        ast-grep scan -r "$rule" $(echo "$CHANGED_FILES" | grep "\\.js$\|\\.ts$")
    done
fi

# Scan changed Python files
if echo "$CHANGED_FILES" | grep -q "\\.py$"; then
    echo "Scanning Python files for route handlers..."
    for rule in generate_sources/rules/python/*.yml; do
        ast-grep scan -r "$rule" $(echo "$CHANGED_FILES" | grep "\\.py$")
    done
fi
```

### VS Code Task

Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Scan All API Routes",
      "type": "shell",
      "command": "${workspaceFolder}/generate_sources/scan-all.sh ${workspaceFolder}",
      "problemMatcher": []
    },
    {
      "label": "Scan JavaScript Routes",
      "type": "shell",
      "command": "ast-grep scan -r ${workspaceFolder}/generate_sources/rules/javascript/express-routes.yml ${workspaceFolder}",
      "problemMatcher": []
    }
  ]
}
```

## Rule Structure

Each rule file follows the ast-grep YAML format:

```yaml
id: unique-rule-id
language: javascript  # or python, java, go, rust, ruby, cpp
rule:
  any:  # Match any of these patterns
    - pattern: $APP.get($PATH, $$$HANDLERS)
    - pattern: $APP.post($PATH, $$$HANDLERS)
message: Express.js route handler found
severity: info
```

### Pattern Variables

- `$VAR` - Match a single AST node
- `$$$VAR` - Match zero or more AST nodes (variadic)
- Patterns can include method calls, decorators, class definitions, etc.

## Output Format

ast-grep outputs matches in this format:

```
file_path:line:column
  rule_id: message
  | code snippet
```

Example:

```
src/routes/users.js:10:1
  express-routes: Express.js route handler found
  | app.get('/users', async (req, res) => {
```

## Common Use Cases

### Security Review

Find all API endpoints for security analysis:

```bash
./scan-all.sh /path/to/codebase security-review.txt
```

### Identify Unauthenticated Routes

Combine with grep to find potentially unauthenticated endpoints:

```bash
ast-grep scan -r rules/python/fastapi-routes.yml . | while read -r line; do
    FILE=$(echo "$line" | cut -d: -f1)
    LINE_NUM=$(echo "$line" | cut -d: -f2)

    # Check if authentication decorator exists nearby
    if ! sed -n "$((LINE_NUM-5)),$((LINE_NUM+2))p" "$FILE" | grep -q "Depends\|auth"; then
        echo "Potential unauthenticated route: $line"
    fi
done
```

### Generate API Inventory

Create a list of all API endpoints:

```bash
./scan-all.sh /path/to/codebase api-inventory.txt
```

### Find Routes with Path Parameters

Look for routes with dynamic parameters (potential injection points):

```bash
ast-grep scan -c rules/go/gin-routes.yml . | grep -E ':\w+|{\w+}'
```

## Customization

### Adding New Rules

To add support for a new framework:

1. Create a new YAML file in the appropriate language directory
2. Define the AST patterns for route handlers
3. Test against sample code
4. Update this README

Example rule for a new framework:

```yaml
id: my-framework-routes
language: python
rule:
  any:
    - pattern: |
        @route($PATH)
        def $HANDLER($$$PARAMS):
            $$$BODY
message: My Framework route handler found
severity: info
```

### Testing Rules

Test a rule against sample code:

```bash
# Create test file
cat > test.py << 'EOF'
@app.get("/test")
def test_route():
    return {"message": "test"}
EOF

# Test the rule
ast-grep scan -r rules/python/fastapi-routes.yml test.py

# Clean up
rm test.py
```

## Performance Tips

### Parallel Scanning

Use GNU parallel for faster multi-rule scanning:

```bash
find rules -name "*.yml" | parallel -j 4 'ast-grep scan -r {} /path/to/project'
```

### Filter Large Codebases

Exclude vendor/dependency directories:

```bash
find /path/to/project \
    -type f \
    -not -path "*/node_modules/*" \
    -not -path "*/vendor/*" \
    -not -path "*/.venv/*" \
    -not -path "*/target/*" \
    \( -name "*.js" -o -name "*.py" -o -name "*.go" -o -name "*.rs" \) \
    -exec ast-grep scan -c rules/javascript/express-routes.yml {} +
```

## Limitations

- **Pattern matching** - AST-based matching is syntax-aware but doesn't understand runtime behavior
- **Dynamic routes** - Dynamically registered routes at runtime may not be detected
- **Custom abstractions** - Project-specific wrappers require additional rules
- **Framework versions** - Rules target common patterns; some version-specific syntax may be missed

## Troubleshooting

### Rule parsing errors

If you see parsing errors, check:
- YAML syntax is valid
- Indentation is correct (use spaces, not tabs)
- Pattern syntax matches the target language

### No matches found

If rules don't find routes:
- Verify the target files use the expected framework
- Check if the framework version uses different syntax
- Try simpler patterns to debug

### Too many false positives

Refine patterns to be more specific:
- Add additional context to patterns
- Use `all` instead of `any` to require multiple conditions
- Add constraints with `where` clauses

## Contributing

Contributions are welcome! To add new rules:

1. Test against real-world codebases
2. Ensure patterns are specific enough to avoid false positives
3. Add clear documentation
4. Update this README with the new framework

## Related Tools

- **ast-grep** - https://ast-grep.github.io/
- **Semgrep** - Pattern-based code scanning
- **CodeQL** - Semantic code analysis
- **Joern** - Code property graph analysis

## License

These rules are provided as examples for security review and code analysis purposes.
