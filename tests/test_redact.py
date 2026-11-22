from app.redact import redact


def test_email_is_removed():
    assert "[EMAIL]" in redact("contact a@b.com today")
    assert "a@b.com" not in redact("contact a@b.com today")


def test_phone_is_removed():
    assert "[PHONE]" in redact("call 9876543210 now")
    assert "9876543210" not in redact("call 9876543210 now")


def test_plain_text_is_unchanged():
    assert redact("my refund is late") == "my refund is late"