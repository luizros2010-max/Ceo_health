from app.auth import hash_password, make_token, parse_token, verify_password


def test_password_hash_roundtrip():
    h = hash_password("s3cret!")
    assert verify_password("s3cret!", h)
    assert not verify_password("wrong", h)
    assert not verify_password("s3cret!", None)
    # different salt each time
    assert hash_password("s3cret!") != hash_password("s3cret!")


def test_session_token_sign_verify():
    t = make_token(42)
    assert parse_token(t) == 42
    assert parse_token(None) is None
    assert parse_token("42.deadbeef") is None      # bad signature
    assert parse_token("not-a-token") is None
