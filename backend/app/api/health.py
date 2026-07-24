from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {
        "status": "running",
        "message": "Backend is working correctly"
    }