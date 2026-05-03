from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/metadata")
def metadata() -> dict:
    return {
        "name": "Vera AI Bot",
        "version": "1.0",
        "description": "AI engagement assistant for merchants",
    }
