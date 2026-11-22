from dotenv import load_dotenv
from fastapi import FastAPI

from app.schemas import TicketIn, TriageResult
from app.store import TriageStore
from app.triage import run_triage

load_dotenv()

app = FastAPI(title="Dhaba triage")
store = TriageStore()


@app.post("/triage", response_model=TriageResult)
def triage(ticket: TicketIn) -> TriageResult:
    return run_triage(ticket, store)