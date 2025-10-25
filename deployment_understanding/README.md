# Deployment Understanding Agent

An AI-powered agent that analyzes both application codebases and Infrastructure as Code (IaC) to create comprehensive **service-level deployment models**. This tool helps security teams understand how services are deployed, their security boundaries, authentication flows, and which services handle user input.

**Focus**: Service-to-service architecture and communication patterns, not individual files or functions.

## Purpose

This agent provides critical context for security reviews by:

- Mapping the complete deployment architecture
- Identifying internet-facing vs internal services
- Documenting authentication and authorization flows between services
- Tracing which services handle arbitrary user input
- Understanding network segmentation and security boundaries
- Providing a reference for other security analysis agents

## Features

- **Multi-IaC Support**: Works with Terraform, AWS CDK, Pulumi, CloudFormation, and other IaC tools
- **Comprehensive Analysis**: Analyzes both code and infrastructure configuration
- **Security Focus**: Emphasizes authentication, authorization, and input handling
- **Detailed Output**: Generates markdown documentation with file references and line numbers
- **Service Mapping**: Creates visual diagrams of service interactions

## Installation

```bash
cd deployment_understanding
npm install
```

## Configuration

Create a `.env` file with your OpenAI API key:

```bash
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4.1-mini  # Optional, defaults to gpt-4.1-mini
```

## Usage

```bash
npm start <codebase-path> <iac-path> [output-path]
```

### Arguments

- `codebase-path` (required): Path to your application codebase or monorepo
- `iac-path` (required): Path to your Infrastructure as Code directory (Terraform, CDK, etc.)
- `output-path` (optional): Output file for the deployment model (default: `deployment_model.md`)

### Examples

```bash
# Analyze a monorepo with Terraform
npm start /path/to/monorepo /path/to/terraform deployment_model.md

# Analyze with AWS CDK
npm start ./app ./infrastructure/cdk ./docs/deployment.md

# Analyze with Pulumi
npm start ../services ../pulumi deployment_analysis.md
```

## Output

The agent generates a comprehensive Markdown document containing:

### 1. Executive Summary
High-level overview of the deployment architecture and key security considerations

### 2. Services Overview
Detailed information about each service:
- Service type and purpose
- Runtime environment
- Repository path
- Deployment target

### 3. Network Topology
- Internet-facing services with load balancer/API gateway configuration
- Internal services with network isolation details
- Visual network diagram showing service relationships

### 4. Authentication & Authorization
- Service-to-service authentication patterns
- User authentication flows
- Authorization models (RBAC, ABAC, etc.)

### 5. Input Sources & Data Flow
- User input entry points
- Service-to-service communication patterns
- Data flow diagrams

### 6. Security Boundaries
- Trust zones (public, application, data)
- Critical security controls
- Network segmentation details

### 7. Infrastructure Resources
- Compute resources
- Networking configuration
- Data stores
- IAM roles and permissions

### 8. Security Considerations
- Attack surface analysis
- Key security questions answered
- Recommendations for improvement

## How It Works

1. **Service Discovery**: Uses OpenAI Codex to identify services in the codebase:
   - Distinct deployable services/components
   - Service boundaries and responsibilities
   - Exposed interfaces (APIs, message queues, databases)
   - Service-to-service communication patterns
   - **Note**: Focuses on service architecture, not individual files/functions

2. **Infrastructure Analysis**: Analyzes IaC configurations to understand:
   - Network topology (VPCs, subnets, load balancers)
   - Security groups and IAM roles
   - Service deployment targets and exposure
   - Network segmentation and trust zones

3. **Architecture Mapping**: Combines both analyses to create:
   - Service dependency graphs showing all communication flows
   - Service communication matrices with protocols and auth methods
   - Network diagrams showing trust boundaries
   - Categorization of services by input source (user-facing vs internal)

## Use Cases

### Security Reviews
Understand the complete attack surface and trust boundaries before conducting security assessments

### Incident Response
Quickly understand service relationships and data flows during security incidents

### Compliance Audits
Document deployment architecture and security controls for compliance requirements

### Architecture Reviews
Review deployment patterns and identify potential security improvements

### Onboarding
Help new team members understand the deployment architecture and security model

## Integration with Other Agents

This agent is designed to provide context for other security analysis tools:

- **Trace Agent**: Uses deployment model to understand which services handle untrusted input
- **Vulnerability Scanners**: Prioritizes scanning of internet-facing services
- **Access Review Tools**: Validates authentication/authorization implementations
- **Penetration Testing**: Identifies entry points and service boundaries

## Example Output Structure

```markdown
# Deployment Model

## Executive Summary
This system deploys 5 microservices in a typical 3-tier architecture on AWS.
The API Gateway handles all external traffic and routes to backend services.
Services communicate via gRPC and message queues. User authentication is
centralized through an Auth Service.

## Services Overview

### Service: api-gateway
- **Type**: API Service
- **Purpose**: External API endpoint, request routing, rate limiting
- **Runtime**: Node.js 18 in Docker
- **Repository Path**: services/api-gateway/
- **Deployment Target**: ECS Fargate behind ALB
- **Exposed Interfaces**:
  - HTTP API: /api/* (REST endpoints)
  - gRPC: None
  - Message Queue: Publishes to 'events' topic
  - Database: Read-only access to cache
- **Dependencies**: auth-service, user-service, order-service
- **Consumed By**: Internet users, mobile apps
- **Handles User Input**: Yes - All external HTTP requests

### Service: auth-service
- **Type**: Authentication Service
- **Purpose**: User authentication, JWT token generation/validation
- **Runtime**: Go 1.21
- **Repository Path**: services/auth/
- **Deployment Target**: ECS Fargate (internal)
- **Exposed Interfaces**:
  - HTTP API: None (internal gRPC only)
  - gRPC: AuthService (Login, ValidateToken, RefreshToken)
  - Message Queue: None
  - Database: PostgreSQL (users, sessions)
- **Dependencies**: None
- **Consumed By**: api-gateway, user-service
- **Handles User Input**: No - Only processes requests from api-gateway

## Service Dependency Graph
```
[Internet] --> [ALB] --> [API Gateway] --gRPC--> [Auth Service] --> [PostgreSQL]
                              |                        ^
                              +--gRPC--> [User Service]|
                              |              |         |
                              +--gRPC--> [Order Service]
                              |
                              +--Pub--> [SQS: events]
                                            |
                                          Sub
                                            v
                              [Worker Service] --> [S3]
```

## Service Communication Matrix
| From | To | Protocol | Auth | Sync/Async | Purpose |
|------|------|----------|------|------------|---------|
| API Gateway | Auth Service | gRPC | mTLS | Sync | Token validation |
| API Gateway | User Service | gRPC | mTLS | Sync | User queries |
| API Gateway | SQS | HTTPS | IAM | Async | Event publishing |
...

## Network Topology
### Internet-Facing Services
- **api-gateway**: Exposed via ALB at api.example.com
  - WAF enabled with rate limiting (1000 req/min)
  - HTTPS only, cert from ACM
...
```

## Limitations

- Requires OpenAI API access and Codex SDK
- Analysis quality depends on code and IaC documentation
- May require manual review for complex or undocumented architectures
- Large codebases may require longer processing times

## Contributing

This is part of the SecurityReview project. See the main repository for contribution guidelines.

## License

ISC
