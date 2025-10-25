#!/usr/bin/env python3
"""Test script for deployment model parser."""

import sys
from pathlib import Path
from deployment_parser import DeploymentModelParser


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_deployment_parser.py <deployment-model.json> <file-path>")
        print("\nExample:")
        print("  python test_deployment_parser.py deployment_model.json app/routes/users.py")
        print("\nThis will test if the file path matches any service in the deployment model.")
        sys.exit(1)

    model_path = Path(sys.argv[1])
    test_path = sys.argv[2]

    if not model_path.exists():
        print(f"Error: Deployment model not found: {model_path}")
        sys.exit(1)

    print(f"Loading deployment model: {model_path}")
    parser = DeploymentModelParser(model_path, debug=True)

    print(f"\nTesting path: {test_path}")
    print("-" * 80)

    context = parser.get_deployment_context(test_path)

    print("-" * 80)
    if context:
        print("\n✅ Match found!")
        print(f"  Service: {context.service_name}")
        print(f"  Trust Zone: {context.trust_zone}")
        print(f"  Network Exposure: {context.network_exposure}")
        print(f"  Deployment Target: {context.deployment_target}")
        print(f"  Auth Method: {context.authentication_method}")
        print(f"  Upstream: {', '.join(context.upstream_services) if context.upstream_services else 'None'}")
        print(f"  Downstream: {', '.join(context.downstream_services) if context.downstream_services else 'None'}")
    else:
        print("\n❌ No match found")
        print("\nTroubleshooting:")
        print("1. Check that the file path matches a repository_paths entry in your deployment model")
        print("2. The parser tries multiple matching strategies:")
        print("   - Exact prefix match (path starts with repo_path/)")
        print("   - Contains match (path contains /repo_path/)")
        print("   - Component match (repo_path appears in path components)")
        print("\nExample repository_paths formats:")
        print('  ["app/", "src/api/"] - relative paths')
        print('  ["backend/"] - directory names')


if __name__ == "__main__":
    main()
