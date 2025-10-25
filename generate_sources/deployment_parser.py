"""Parser for deployment model JSON files."""

import json
from pathlib import Path
from typing import Optional
from models import DeploymentContext


class DeploymentModelParser:
    """Parses deployment model JSON and provides deployment context."""

    def __init__(self, json_path: Path, debug: bool = False):
        """
        Initialize parser with JSON file.

        Args:
            json_path: Path to deployment model JSON file
            debug: Enable debug logging
        """
        self.json_path = json_path
        self.model = {}
        self.services = {}
        self.trust_zones = []
        self.debug = debug
        self._load()

    def _load(self):
        """Load and parse the JSON file."""
        if not self.json_path.exists():
            print(f"Warning: Deployment model file not found: {self.json_path}")
            return

        try:
            with open(self.json_path, 'r') as f:
                self.model = json.load(f)

            self.services = self.model.get('services', {})
            self.trust_zones = self.model.get('trust_zones', [])

        except json.JSONDecodeError as e:
            print(f"Error parsing deployment model JSON: {e}")
            print(f"File: {self.json_path}")
        except Exception as e:
            print(f"Error loading deployment model: {e}")

    def get_deployment_context(self, file_path: str) -> Optional[DeploymentContext]:
        """
        Get deployment context for a given file path.

        Args:
            file_path: Path to the source file

        Returns:
            DeploymentContext if service is found, None otherwise
        """
        if not self.services:
            return None

        # Normalize the file path - handle both absolute and relative paths
        normalized_path = file_path.replace('\\', '/').lower()

        # Try to extract just the relative path part
        # Common patterns: /full/path/to/repo/app/file.py -> app/file.py
        path_parts = normalized_path.split('/')

        # Find matching service by checking repository_paths
        matched_service = None
        matched_service_name = None
        best_match_length = 0

        for service_name, service_info in self.services.items():
            repo_paths = service_info.get('repository_paths', [])

            # Check if file path contains or starts with any of the repository paths
            for repo_path in repo_paths:
                normalized_repo_path = repo_path.replace('\\', '/').lower().strip('/')

                # Try multiple matching strategies:
                # 1. Exact prefix match
                if normalized_path.startswith(normalized_repo_path + '/'):
                    match_length = len(normalized_repo_path)
                    if match_length > best_match_length:
                        matched_service = service_info
                        matched_service_name = service_name
                        best_match_length = match_length

                # 2. Path contains the repo path (for absolute paths)
                elif ('/' + normalized_repo_path + '/') in normalized_path:
                    match_length = len(normalized_repo_path)
                    if match_length > best_match_length:
                        matched_service = service_info
                        matched_service_name = service_name
                        best_match_length = match_length

                # 3. Check if any path component matches
                elif normalized_repo_path in path_parts:
                    match_length = len(normalized_repo_path)
                    if match_length > best_match_length:
                        matched_service = service_info
                        matched_service_name = service_name
                        best_match_length = match_length

        if not matched_service:
            if self.debug:
                print(f"  ⚠ No service match for: {file_path}")
                print(f"    Available services: {list(self.services.keys())}")
                print(f"    Tried matching against paths:")
                for svc_name, svc_info in self.services.items():
                    paths = svc_info.get('repository_paths', [])
                    if paths:
                        print(f"      {svc_name}: {paths}")
            return None

        if self.debug:
            print(f"  ✓ Matched {file_path} -> {matched_service_name}")

        # Determine trust zone for this service
        trust_zone = None
        for zone in self.trust_zones:
            if matched_service_name in zone.get('services', []):
                trust_zone = zone.get('name')
                break

        # Get authentication method
        # First check service-to-service comms where this is the "from" service
        auth_method = None
        communications = self.model.get('communications', [])
        for comm in communications:
            if comm.get('from_service') == matched_service_name:
                auth_method = comm.get('auth_method')
                break

        # Fall back to user auth method if no service auth found
        if not auth_method:
            auth_method = self.model.get('user_authentication_method')

        return DeploymentContext(
            service_name=matched_service.get('name', matched_service_name),
            trust_zone=trust_zone,
            network_exposure=matched_service.get('network_exposure', 'Internal only'),
            authentication_method=auth_method,
            deployment_target=matched_service.get('deployment_target'),
            upstream_services=matched_service.get('upstream_services', []),
            downstream_services=matched_service.get('downstream_services', [])
        )
