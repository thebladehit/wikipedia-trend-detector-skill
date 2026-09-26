"""Retry behaviour of http._download without network: _request is replaced."""
import email.message
import urllib.error

import pytest

from wikitrends import http


def _http_error(code, retry_after=None):
    headers = email.message.Message()
    if retry_after:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError("http://x", code, "err", headers, None)


@pytest.fixture
def fake(monkeypatch):
    sleeps = []
    monkeypatch.setattr(http.time, "sleep", sleeps.append)

    def install(*responses):
        queue = list(responses)

        def request(url):
            r = queue.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        monkeypatch.setattr(http, "_request", request)
        return sleeps
    return install


def test_5xx_is_retried_with_backoff(fake):
    sleeps = fake(_http_error(503), _http_error(502), "ok")
    assert http._download("u", allow_404=False) == "ok"
    assert sleeps == [1.0, 2.0]


def test_429_waits_retry_after(fake):
    sleeps = fake(_http_error(429, "7"), "ok")
    assert http._download("u", allow_404=False) == "ok"
    assert sleeps == [7.0]


def test_429_with_too_long_wait_fails(fake):
    fake(_http_error(429, "120"))
    with pytest.raises(http.WitError) as e:
        http._download("u", allow_404=False)
    assert e.value.code == "rate_limited"


def test_allowed_404_is_no_data(fake):
    fake(_http_error(404))
    assert http._download("u", allow_404=True) is None


def test_other_4xx_fails_immediately(fake):
    sleeps = fake(_http_error(400))
    with pytest.raises(http.WitError) as e:
        http._download("u", allow_404=True)
    assert e.value.code == "http_error" and sleeps == []


def test_network_error_after_all_retries(fake):
    sleeps = fake(*[urllib.error.URLError("down")] * (http.MAX_RETRIES + 1))
    with pytest.raises(http.WitError) as e:
        http._download("u", allow_404=False)
    assert e.value.code == "network_error" and sleeps == [1.0, 2.0, 4.0, 8.0]
