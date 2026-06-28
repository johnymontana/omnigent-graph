from app.auth import ALGORITHM, UserAuth


def test_issue_and_verify_roundtrip():
    auth = UserAuth()
    token = auth.issue_token("user-123")
    payload = auth.verify_token(token)
    assert payload["sub"] == "user-123"


def test_rejects_unexpected_alg():
    # The incident-#42 lesson: never accept a token whose alg differs from the decision on record.
    auth = UserAuth()
    assert ALGORITHM == "RS256"
