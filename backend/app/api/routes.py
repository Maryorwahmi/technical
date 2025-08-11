from fastapi import APIRouter
from app.signals.signal_engine import SignalEngine

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/signals")
def get_signals():
    # Placeholder for signal fetching
    return {"signals": []}
