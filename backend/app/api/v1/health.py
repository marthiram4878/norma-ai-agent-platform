"""Liveness and readiness API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.config import settings
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services.readiness import ReadinessReport, check_dependencies

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Service liveness")
async def health_check() -> HealthResponse:
    """Confirm that the API process can serve requests."""

    return HealthResponse(status="ok", service=settings.app_name, version="v1")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Infrastructure readiness",
    responses={503: {"model": ReadinessResponse}},
)
async def readiness_check(
    response: Response,
    report: Annotated[ReadinessReport, Depends(check_dependencies)],
) -> ReadinessResponse:
    """Report whether required infrastructure can accept work."""

    if not report.is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if report.is_ready else "degraded",
        checks={
            name: "ok" if available else "unavailable"
            for name, available in report.checks.items()
        },
    )
