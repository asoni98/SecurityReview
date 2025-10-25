"""Pydantic models for security analysis output."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level classification for user input handlers."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class InputSource(str, Enum):
    """Types of user input sources."""
    HTTP_BODY = "http_body"
    HTTP_HEADERS = "http_headers"
    URL_PARAMS = "url_params"
    QUERY_PARAMS = "query_params"
    PATH_PARAMS = "path_params"
    GRAPHQL_ARGS = "graphql_args"
    GRPC_REQUEST = "grpc_request"
    WEBSOCKET = "websocket"
    FILE_UPLOAD = "file_upload"
    COOKIES = "cookies"
    UNKNOWN = "unknown"


class VulnerabilityType(str, Enum):
    """Potential vulnerability types."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    SSRF = "ssrf"
    XXE = "xxe"
    DESERIALIZATION = "deserialization"
    IDOR = "idor"
    MASS_ASSIGNMENT = "mass_assignment"
    AUTHENTICATION_BYPASS = "authentication_bypass"
    AUTHORIZATION_BYPASS = "authorization_bypass"
    BUSINESS_LOGIC = "business_logic"
    OTHER = "other"


class SecurityConcern(BaseModel):
    """A specific security concern identified in the code."""
    vulnerability_type: VulnerabilityType
    description: str = Field(..., description="Explanation of the security concern")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")


class CodeLocation(BaseModel):
    """Location of code in the repository."""
    file_path: str
    line_number: int
    column: Optional[int] = None
    snippet: Optional[str] = None


class FunctionAnalysis(BaseModel):
    """Analysis of a single function handling user input."""
    function_name: str
    location: CodeLocation
    framework: str = Field(..., description="Web framework or library (e.g., Express, FastAPI, Spring)")
    language: str = Field(..., description="Programming language (e.g., javascript, python, java)")

    # Input analysis
    input_sources: List[InputSource] = Field(
        default_factory=list,
        description="Types of user input this function handles"
    )
    accepts_unauthenticated_input: bool = Field(
        ...,
        description="Whether the function accepts input from unauthenticated users"
    )

    # Security analysis
    risk_level: RiskLevel
    security_concerns: List[SecurityConcern] = Field(
        default_factory=list,
        description="Identified security concerns"
    )

    # Context
    endpoint_path: Optional[str] = Field(
        None,
        description="API endpoint path if identifiable"
    )
    http_methods: List[str] = Field(
        default_factory=list,
        description="HTTP methods (GET, POST, etc.)"
    )

    # Additional context
    has_input_validation: Optional[bool] = Field(
        None,
        description="Whether input validation is present"
    )
    has_sanitization: Optional[bool] = Field(
        None,
        description="Whether input sanitization is present"
    )
    has_authorization_check: Optional[bool] = Field(
        None,
        description="Whether authorization checks are present"
    )

    reasoning: str = Field(
        ...,
        description="Explanation of the risk assessment and prioritization"
    )


class PrioritizedFindings(BaseModel):
    """Complete prioritized list of findings for security review."""
    total_functions_analyzed: int
    high_priority_count: int = Field(
        ...,
        description="Number of CRITICAL and HIGH risk functions"
    )

    findings: List[FunctionAnalysis] = Field(
        ...,
        description="Functions prioritized by risk level (highest first)"
    )

    summary: str = Field(
        ...,
        description="Executive summary of the analysis"
    )

    recommendations: List[str] = Field(
        default_factory=list,
        description="General security recommendations"
    )


class AstGrepFinding(BaseModel):
    """Parsed ast-grep scan finding."""
    file_path: str
    line_number: int
    column: int
    rule_id: str
    message: str
    code_snippet: str
    framework: str
    language: str
