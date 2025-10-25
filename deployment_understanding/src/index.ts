import { Codex } from "@openai/codex-sdk";
import { writeFileSync } from "fs";
import { runPrompt } from "./openaiClient.js";
import { buildDeploymentAnalysisPrompt } from "../prompts/deploymentAnalysis.js";

async function main() {
    // Parse command line arguments
    const codebasePath = process.argv[2];
    const iacPath = process.argv[3];
    const outputPath = process.argv[4] ?? "./deployment_model.md";

    if (!codebasePath || !iacPath) {
        console.error("Usage: npm start <codebase-path> <iac-path> [output-path]");
        console.error("\nExample:");
        console.error("  npm start /path/to/monorepo /path/to/terraform deployment_model.md");
        console.error("\nArguments:");
        console.error("  codebase-path  Path to the application codebase/monorepo");
        console.error("  iac-path       Path to Infrastructure as Code (Terraform/CDK/Pulumi)");
        console.error("  output-path    Output file for deployment model (default: deployment_model.md)");
        process.exit(1);
    }

    console.log("🔍 Analyzing deployment architecture...");
    console.log(`📁 Codebase: ${codebasePath}`);
    console.log(`🏗️  IaC: ${iacPath}`);
    console.log(`📝 Output: ${outputPath}\n`);

    const codex = new Codex();

    // Step 1: Gather codebase context
    console.log("📊 Step 1: Analyzing codebase structure and services...");
    const codebaseThread = codex.startThread();
    const codebasePrompt = `
Analyze the codebase at ${codebasePath} with a focus on SERVICE-LEVEL architecture, not individual files or functions.

**PRIMARY GOAL**: Identify distinct services and map how they communicate with each other.

1. **Service Identification** (focus on architectural boundaries):
   - List all deployable services/components (look for separate directories, docker-compose services, separate package.json files, etc.)
   - For each service, identify:
     * Service name and purpose
     * Technology stack (Node.js, Python, Go, etc.)
     * Entry point (main.ts, app.py, index.js, etc.)
     * Directory/path in monorepo

2. **Service Interfaces** (what each service exposes):
   - HTTP/REST APIs: List endpoint patterns (e.g., /api/users/*, /api/orders/*) rather than individual routes
   - GraphQL: Schema files and main query/mutation groups
   - gRPC: Service definitions from .proto files
   - Message Queue Topics: What topics/queues does this service publish to or consume from?
   - Databases: What databases does this service own/access?

3. **Inter-Service Communication Patterns**:
   - Service A calls Service B: What is the communication protocol? (HTTP, gRPC, message queue)
   - Map service dependencies: Which services depend on which other services?
   - Identify service discovery mechanisms (hardcoded URLs, env vars, service mesh, DNS)
   - Note async vs synchronous communication patterns

4. **Authentication/Authorization Architecture** (service-level, not function-level):
   - How does each service authenticate incoming requests? (JWT, API keys, mTLS, IAM roles)
   - How do services authenticate TO each other? (service accounts, API keys, IAM roles)
   - Which services enforce authorization and how? (middleware, gateway, per-service)
   - Identity providers or auth services

5. **User Input Entry Points** (service-level):
   - Which services accept direct user input (web requests, file uploads, webhooks)?
   - Which services only process data from other internal services?
   - What validation/sanitization patterns exist at service boundaries?

**IMPORTANT**:
- Focus on SERVICE boundaries and SERVICE-to-SERVICE communication
- Do NOT trace individual function calls within a service
- Provide service-level architecture, not implementation details
- Include directory paths for services, but avoid detailed file-by-file analysis
- Summarize patterns rather than listing every file
`;

    const codebaseResult = await codebaseThread.run(codebasePrompt);
    console.log("✅ Codebase analysis complete\n");

    // Step 2: Gather IaC context
    console.log("🏗️  Step 2: Analyzing infrastructure configuration...");
    const iacThread = codex.startThread();
    const iacPrompt = `
Analyze the Infrastructure as Code at ${iacPath} and provide:

1. **IaC Tool & Structure**:
   - Identify the IaC tool(s) used (Terraform, CDK, Pulumi, CloudFormation, etc.)
   - List main configuration files and modules

2. **Compute Resources**:
   - EC2 instances, ECS/EKS clusters, Lambda functions
   - Auto-scaling groups, instance types
   - Container definitions and task definitions

3. **Network Architecture**:
   - VPCs, subnets (public/private), route tables
   - Internet gateways, NAT gateways
   - Load balancers (ALB, NLB, API Gateway)
   - DNS configuration (Route53, etc.)

4. **Security Configuration**:
   - Security groups, NACLs
   - IAM roles, policies, and permissions
   - Service accounts, assume role policies
   - WAF rules, rate limiting

5. **Service Exposure**:
   - Which services have public IPs or load balancers
   - Ingress/egress rules for each service
   - Port configurations

6. **Data Resources**:
   - RDS databases, DynamoDB tables
   - S3 buckets, ElastiCache, etc.
   - Access policies and encryption

7. **Service Discovery & Communication**:
   - Service mesh configuration (Istio, Linkerd, etc.)
   - Internal DNS, service discovery
   - API gateway configurations

Provide detailed information with file paths and line numbers.
Include actual configuration snippets for critical security settings.
`;

    const iacResult = await iacThread.run(iacPrompt);
    console.log("✅ Infrastructure analysis complete\n");

    // Step 3: Generate deployment model
    console.log("📝 Step 3: Generating deployment model...");
    const deploymentModel = await runPrompt(
        buildDeploymentAnalysisPrompt({
            codebaseContext: codebaseResult.finalResponse,
            iacContext: iacResult.finalResponse,
        })
    );

    // Write to output file
    writeFileSync(outputPath, deploymentModel, "utf8");
    console.log(`\n✅ Deployment model written to: ${outputPath}`);
    console.log("\n📖 Review the deployment model to understand:");
    console.log("   - Which services are internet-facing vs internal");
    console.log("   - Authentication and authorization flows");
    console.log("   - Service-to-service communication patterns");
    console.log("   - Which services handle user input");
}

export default main();
