from fastapi import APIRouter

router = APIRouter(prefix="/api/salesforce", tags=["salesforce"])


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "TODO"}
