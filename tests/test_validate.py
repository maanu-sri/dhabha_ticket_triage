import json

from app.validate import get_validated_output, parse_model_output

GOOD = json.dumps({
    "category": "refund_request",
    "severity": "high",
    "reply_draft": "Hi, we are looking into it.",
    "confidence": 0.9,
})


def test_valid_json_is_accepted():
    assert parse_model_output(GOOD) is not None


def test_prose_is_rejected():
    assert parse_model_output("Sure! Here is the answer.") is None


def test_invented_category_is_rejected():
    bad = json.dumps({"category": "random", "severity": "high", "reply_draft": "Hi", "confidence": 0.9})
    assert parse_model_output(bad) is None


def test_refund_from_model_is_rejected():
    bad = json.dumps({"category": "refund_request", "severity": "high", "reply_draft": "Hi", "confidence": 0.9, "refund": 999})
    assert parse_model_output(bad) is None


def test_retry_returns_good_second_answer():
    answers = iter(["not json", GOOD])
    assert get_validated_output(lambda _: next(answers), "ticket") is not None


def test_gives_up_after_two_bad_answers():
    assert get_validated_output(lambda _: "bad", "ticket") is None