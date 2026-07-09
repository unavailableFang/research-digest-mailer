from research_digest.mailer import _clean_secret


def test_clean_secret_removes_visible_and_nonbreaking_spaces():
    assert _clean_secret("abcd efgh\u00a0ijkl mnop") == "abcdefghijklmnop"
