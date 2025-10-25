interface BuildDeploymentAnalysisPromptParams {
    codebaseContext: string;
    iacContext: string;
}

export function buildDeploymentAnalysisPrompt({
    codebaseContext,
    iacContext,
}: BuildDeploymentAnalysisPromptParams): string {
    return `You are a deployment infrastructure and security architecture expert.
Your task is to analyze both application code and Infrastructure as Code (IaC) to create
a comprehensive deployment model focused on SERVICE-LEVEL architecture, showing how services
are deployed, how they interact, and their security boundaries.

**IMPORTANT**: Focus on service-to-service relationships and architectural patterns, NOT on
individual files, functions, or implementation details.

<analysis_process>
1. Identify all deployable services/components as logical units
2. Analyze IaC configurations to understand deployment topology and network architecture
3. Map service communication patterns and dependencies
4. Identify authentication and authorization flows between services
5. Determine which services are internet-facing vs internal
6. Trace data flow at the service level (not function level)
7. Categorize input sources by service (user-facing vs internal-only)
</analysis_process>

<thinking>
<service_architecture>
- What distinct services/components exist as deployable units?
- What is the overall architecture pattern (microservices, monolith, hybrid, serverless)?
- What are the service boundaries and responsibilities?
- How are services organized (by domain, by function, etc.)?
</service_architecture>

<infrastructure_topology>
- What deployment infrastructure is provisioned (compute, networking, storage)?
- What network zones exist (public, private, data)?
- How are services distributed across infrastructure?
- What load balancers, API gateways, or service meshes exist?
</infrastructure_topology>

<service_communication>
- Which services communicate with which other services?
- What protocols are used (HTTP/REST, gRPC, message queues, database)?
- What are the communication patterns (sync vs async, request/response vs pub/sub)?
- How is service discovery handled?
</service_communication>

<authentication_flows>
- How do external users/clients authenticate to the system?
- How do services authenticate to each other (service accounts, mTLS, IAM)?
- Where are authorization decisions made (gateway, per-service, centralized)?
- What identity providers or auth services exist?
</authentication_flows>

<security_boundaries>
- Which services are exposed to the internet?
- Which services are internet-facing but behind gateways/WAF?
- Which services are internal-only?
- What network segmentation exists between services?
- Which services handle untrusted user input directly?
</security_boundaries>
</thinking>

<codebase_context>
${codebaseContext}
</codebase_context>

<iac_context>
${iacContext}
</iac_context>

<output_format>
Create a comprehensive Markdown document with the following structure:

# Deployment Model

## Executive Summary
Brief overview of the deployment architecture and key security considerations.

## Services Overview

### Service: [Service Name]
- **Type**: [API Service / Worker / Background Job / etc.]
- **Purpose**: [Brief description of service responsibility]
- **Runtime**: [Node.js / Python / Go / etc.]
- **Repository Path**: [services/service-name/] (directory only, not individual files)
- **Deployment Target**: [ECS / Lambda / K8s / EC2 / etc.]
- **Exposed Interfaces**:
  - HTTP API: [Yes/No - endpoint patterns like /api/users/*]
  - gRPC: [Yes/No - service definitions]
  - Message Queue: [Topics published to / consumed from]
  - Database: [Owns/accesses which databases]
- **Dependencies**: [List of other services this service calls]
- **Consumed By**: [List of services that call this service]
- **Handles User Input**: [Yes/No - Direct user input or internal only]

## Network Topology
### Internet-Facing Services
List all services exposed to the internet with:
- Load balancer/API gateway configuration
- Public endpoints
- Rate limiting / WAF configuration

### Internal Services
List all internal-only services with:
- Network isolation details (VPC, subnets, security groups)
- Access restrictions

### Service Dependency Graph
Create a visual diagram showing service relationships and communication patterns:
\`\`\`
[Internet/Users]
       |
       v
[Load Balancer / API Gateway]
       |
       +---> [API Service] <---(HTTP)---> [Auth Service]
       |         |                              |
       |         +---(gRPC)---> [User Service]  |
       |         |                   |          |
       |         +---(Pub)-----> [Message Queue]
       |                             |
       |                           (Sub)
       |                             v
       +---> [Worker Service] ---(SQL)---> [Database]
                                                |
                                            [Cache]
\`\`\`

### Communication Protocols
For each service-to-service connection:
- **From → To**: Protocol, Auth Method, Data Type
- Example: \`API Service → User Service\`: gRPC, mTLS, User Data

## Authentication & Authorization

### Service-to-Service Authentication
- **Pattern**: [IAM Roles / Service Accounts / mTLS / API Keys]
- **Implementation Details**: [specific configurations]

### User Authentication
- **Pattern**: [JWT / OAuth / Session-based]
- **Provider**: [Auth0 / Cognito / Custom]
- **Token Flow**: [description]

### Authorization Model
- **Type**: [RBAC / ABAC / ACL]
- **Implementation**: [description]

## Input Sources & Data Flow

### User Input Entry Points
For each service that accepts user input:
- **Service**: [name]
- **Input Type**: [HTTP requests / WebSocket / File upload / etc.]
- **Validation**: [what validation exists]
- **Rate Limiting**: [configuration]

### Service Communication Matrix
Create a table documenting all service-to-service communication:

| From Service | To Service | Protocol | Auth Method | Sync/Async | Data Type | Purpose |
|-------------|------------|----------|-------------|------------|-----------|---------|
| API Service | User Service | gRPC | mTLS | Sync | User queries | User data retrieval |
| API Service | Message Queue | AMQP | IAM Role | Async | Events | Task processing |
| Worker Service | Message Queue | AMQP | IAM Role | Async | Events | Task consumption |
| Worker Service | Database | PostgreSQL | IAM Auth | Sync | Records | Data persistence |

## Security Boundaries

### Trust Zones
- **Public Zone**: Services exposed to internet
- **Application Zone**: Internal application services
- **Data Zone**: Databases and data stores

### Critical Security Controls
- Network segmentation
- Authentication mechanisms
- Authorization enforcement points
- Input validation boundaries

## Infrastructure Resources

### Compute
- List all compute resources (EC2, Lambda, ECS tasks, etc.)

### Networking
- VPCs, subnets, routing tables
- Load balancers, API gateways
- Security groups, NACLs

### Data Stores
- Databases, caches, object storage
- Access patterns and security

### IAM & Permissions
- Service roles
- User roles
- Permission boundaries

## Security Considerations

### Attack Surface
- Internet-facing endpoints
- User input handling services
- Authentication endpoints

### Key Security Questions
- Which services can be reached from the internet?
- How is authentication enforced at each boundary?
- What services handle untrusted user input?
- How are secrets managed?
- What monitoring/logging exists?

## Recommendations
List any security concerns or recommendations for improvement.

</output_format>

<critical_requirements>
**PRIMARY FOCUS**: Service-level architecture and inter-service relationships

- Identify and name all distinct services/components
- Clearly distinguish between internet-facing and internal services
- Document ALL service-to-service authentication and authorization patterns
- Create complete service dependency graphs showing all communication flows
- Categorize services by input source (user-facing vs internal-only)
- Focus on ARCHITECTURAL patterns, not implementation details
- If information is unclear or missing, explicitly note it
- Do NOT include individual file paths, line numbers, or function names
- Provide service directory paths only (e.g., "services/api-gateway/")
- Emphasize security boundaries, trust zones, and network segmentation
- Create visual diagrams that show service relationships clearly
</critical_requirements>`;
}
