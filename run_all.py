import json
from pathlib import Path

from dotenv import load_dotenv

from app.schemas import TicketIn
from app.store import TriageStore
from app.triage import run_triage

load_dotenv()

DATA = Path("data/dhaba_tickets.json")
OUT = Path("results.json")


def main() -> None:
    tickets = json.loads(DATA.read_text(encoding="utf-8"))["tickets"]
    store = TriageStore()
    results = []

    for raw in tickets:
        ticket = TicketIn.model_validate(raw)
        result = run_triage(ticket, store)
        results.append(result.model_dump(mode="json"))
        print(
            f"{result.ticket_id}: refund={result.refund.decision} "
            f"amount={result.refund.amount_inr} needs_human={result.needs_human} "
            f"source={result.source}"
        )

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(results)} results to {OUT}")


if __name__ == "__main__":
    main()