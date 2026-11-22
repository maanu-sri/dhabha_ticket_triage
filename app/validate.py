import json

from pydantic import ValidationError

from app.schemas import ModelOutput


def parse_model_output(raw: str) -> ModelOutput | None:
    """Return a valid ModelOutput, or None if the text is not usable."""
    text = raw.strip().strip("`").strip()
    # Some models wrap JSON in a "json" label; remove it.
    if text.startswith("json"):
        text = text[4:].strip()
    try:
        return ModelOutput.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError):
        return None


def get_validated_output(call_model, ticket_text: str) -> ModelOutput | None:
    """Call the model, retry once if the output is bad, then give up."""
    for _ in range(2):
        result = parse_model_output(call_model(ticket_text))
        if result is not None:
            return result
    return None