"""Pydantic models for deployment model JSON schema."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class ServiceInfo(BaseModel):
    """Information about a deployed service."""
    name: str = Field(..., description="Service name (e.g., yoctogram-api)")
    type: str = Field(..., description="Service type (e.g., API Service, Database)")
    purpose: str = Field(..., description="What the service does")
    runtime: Optional[str] = Field(None, description="Runtime environment")
    deployment_target: Optional[str] = Field(None, description="Where deployed (ECS, Lambda, etc.)")
    handles_user_input: bool = Field(False, description="Whether service accepts external user input")
    network_exposure: str = Field("Internal only", description="Internet-facing or Internal only")

    # Dependencies
    upstream_services: List[str] = Field(
        default_factory=list,
        description="Services that call this service"
    )
    downstream_services: List[str] = Field(
        default_factory=list,
        description="Services this service calls"
    )

    # Code mapping
    repository_paths: List[str] = Field(
        default_factory=list,
        description="File paths/patterns that belong to this service (e.g., app/, src/api/)"
    )


class CommunicationProtocol(BaseModel):
    """Service-to-service communication details."""
    from_service: str
    to_service: str
    protocol: str = Field(..., description="e.g., HTTPS REST, SQL, gRPC")
    auth_method: str = Field(..., description="e.g., OAuth2 JWT, IAM Role, mTLS")
    sync_async: str = Field("Sync", description="Synchronous or Asynchronous")
    data_type: Optional[str] = Field(None, description="Type of data exchanged")


class TrustZone(BaseModel):
    """Security trust zone definition."""
    name: str = Field(..., description="Zone name (e.g., Public Zone, Application Zone)")
    description: str = Field(..., description="What this zone represents")
    services: List[str] = Field(
        default_factory=list,
        description="Services in this trust zone"
    )


class DeploymentModel(BaseModel):
    """Complete deployment model for an application."""

    # Metadata
    application_name: str = Field(..., description="Name of the application")
    description: Optional[str] = Field(None, description="Brief description")

    # Core components
    services: Dict[str, ServiceInfo] = Field(
        default_factory=dict,
        description="Map of service name to service info"
    )

    trust_zones: List[TrustZone] = Field(
        default_factory=list,
        description="Security trust zones"
    )

    communications: List[CommunicationProtocol] = Field(
        default_factory=list,
        description="Service-to-service communications"
    )

    # Network topology
    internet_facing_endpoints: List[str] = Field(
        default_factory=list,
        description="Publicly accessible endpoints/services"
    )

    # Authentication
    user_authentication_method: Optional[str] = Field(
        None,
        description="How users authenticate (e.g., OAuth2 JWT)"
    )

    service_authentication_methods: List[str] = Field(
        default_factory=list,
        description="How services authenticate to each other"
    )
