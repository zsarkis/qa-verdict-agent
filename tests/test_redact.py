from qa_agent.redact import redact


def test_email_redacted():
    text, log = redact("contact dana.whitfield@acmemail.com please")
    assert "dana.whitfield@acmemail.com" not in text
    assert "[REDACTED:EMAIL]" in text
    assert log == ["EMAIL:1"]


def test_phone_redacted():
    text, log = redact("call 555-867-5309 today")
    assert "555-867-5309" not in text
    assert "[REDACTED:PHONE]" in text
    assert log == ["PHONE:1"]


def test_card_redacted_not_treated_as_phone():
    text, log = redact("card 4111 1111 1111 1111 was charged")
    assert "4111" not in text
    assert "[REDACTED:CARD]" in text
    assert log == ["CARD:1"]


def test_ssn_redacted():
    text, log = redact("ssn 123-45-6789 on file")
    assert "[REDACTED:SSN]" in text
    assert log == ["SSN:1"]


def test_clean_text_untouched():
    text, log = redact("orders of 10 or more items ship free")
    assert text == "orders of 10 or more items ship free"
    assert log == []


def test_qa108_ticket_body_fully_scrubbed():
    body = (
        "Reported by customer Dana Whitfield (dana.whitfield@acmemail.com, 555-867-5309). "
        "'My card 4111 1111 1111 1111 shows the same.'"
    )
    text, log = redact(body)
    for pii in ("acmemail.com", "555-867-5309", "4111"):
        assert pii not in text
    assert sorted(log) == ["CARD:1", "EMAIL:1", "PHONE:1"]


def test_log_reports_types_and_counts_never_values():
    _, log = redact("a@b.io and c@d.io")
    assert log == ["EMAIL:2"]
    assert all("@" not in entry for entry in log)
