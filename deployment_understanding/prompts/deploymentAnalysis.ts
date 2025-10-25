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
Output ONLY valid JSON (no markdown, no code fences, no additional text) matching this exact schema:

{
  "application_name": "string - name of the application",
  "description": "string - brief overview of deployment architecture",

  "services": {
    "service-name": {
      "name": "string - service name",
      "type": "string - API Service / Worker / Database / etc.",
      "purpose": "string - brief description",
      "runtime": "string - Node.js / Python / Go / etc.",
      "deployment_target": "string - ECS / Lambda / K8s / etc.",
      "handles_user_input": boolean,
      "network_exposure": "string - Internet-facing or Internal only",
      "upstream_services": ["list of services that call this service"],
      "downstream_services": ["list of services this calls"],
      "repository_paths": ["app/", "services/api/"]
    }
  },

  "trust_zones": [
    {
      "name": "Public Zone",
      "description": "Services exposed to internet",
      "services": ["service-name-1", "service-name-2"]
    },
    {
      "name": "Application Zone",
      "description": "Internal application services",
      "services": ["service-name-3"]
    },
    {
      "name": "Data Zone",
      "description": "Databases and data stores",
      "services": ["database-1", "cache-1"]
    }
  ],

  "communications": [
    {
      "from_service": "api-service",
      "to_service": "database",
      "protocol": "SQL over TCP / HTTPS REST / gRPC / etc.",
      "auth_method": "IAM Role / mTLS / JWT / etc.",
      "sync_async": "Sync or Async",
      "data_type": "User data / Events / etc."
    }
  ],

  "internet_facing_endpoints": [
    "api-service",
    "web-frontend"
  ],

  "user_authentication_method": "OAuth2 JWT / SAML / etc.",

  "service_authentication_methods": [
    "IAM Roles",
    "mTLS",
    "Service accounts"
  ]
}

**CRITICAL REQUIREMENTS**:
1. Output MUST be valid JSON that can be parsed by JSON.parse()
2. Do NOT wrap in markdown code fences (no \`\`\`json)
3. Do NOT include any text before or after the JSON
4. Include ALL services found in the codebase
5. Map file paths to services using "repository_paths" array
6. Identify which services are internet-facing vs internal
7. Document ALL service-to-service communications
8. If information is unclear, use null or empty array, don't omit fields

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
