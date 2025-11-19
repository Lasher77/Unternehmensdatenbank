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

    if token:
        # Some clients (e.g. copy/pasted curl commands) may surround the token in
        # quotes. Strip them to make the comparison more forgiving without
        # reducing security since the configured token cannot contain quotes
        # anyway.
        stripped = token.strip()
        if stripped.startswith(('"', "'")) and stripped.endswith(('"', "'")):
            token = stripped[1:-1]
        else:
            token = stripped

    if scheme.lower() != "bearer" or not token or token != expected_token:
        raise HTTPException(
            status_code=401, detail="Invalid or missing bearer token"
        )

    return {"integration": "salesforce"}
