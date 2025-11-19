"""Authentication dependencies for FastAPI routers."""

from fastapi import Header, HTTPException
from fastapi.security.utils import get_authorization_scheme_param

from ..config import get_settings

settings = get_settings()


def require_salesforce_bearer_token(
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    """Validate the Salesforce matching bearer token."""

    expected_token = settings.salesforce_match_api_token
    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="Salesforce match token not configured",
        )

    if not authorization:
        raise HTTPException(
            status_code=401, detail="Invalid or missing bearer token"
        )

    scheme, token = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer" or not token or token != expected_token:
        raise HTTPException(
            status_code=401, detail="Invalid or missing bearer token"
        )

    return {"integration": "salesforce"}
