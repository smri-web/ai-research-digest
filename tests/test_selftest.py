import selftest


def test_missing_creds_returns_false(monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    # No credentials -> must fail cleanly (return False), never raise.
    assert selftest.send_via_gmail("subject", "<p>hi</p>", "a@b.com") is False
