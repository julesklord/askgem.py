"""
Unit tests for the web research tools (Google Search & DuckDuckGo).
"""

import asyncio
import json
import socket
from unittest.mock import MagicMock, patch

import pytest

from askgem.tools.web_tools import is_safe_url, web_fetch, web_search


@pytest.fixture
def mock_google_response():
    """Mock JSON response for Google Custom Search."""
    return json.dumps(
        {
            "items": [
                {"title": "Result 1", "link": "https://example.com/1", "snippet": "Snippet 1"},
                {"title": "Result 2", "link": "https://example.com/2", "snippet": "Snippet 2"},
            ]
        }
    ).encode("utf-8")


@pytest.fixture
def mock_html_page():
    """Mock HTML content for web_fetch."""
    return b"""
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Title</h1>
            <p>This is a <a href='#'>test</a> of the system.</p>
            <script>console.log('Ignore me');</script>
            <style>.hidden { display: none; }</style>
            <div>Actual content here.</div>
        </body>
    </html>
    """


@patch("urllib.request.urlopen")
@pytest.mark.asyncio
async def test_web_search_google_success(mock_url_open, mock_google_response):
    """Verifies Google Search integration with valid results."""
    mock_response = MagicMock()
    mock_response.read.return_value = mock_google_response
    mock_response.__enter__.return_value = mock_response
    mock_url_open.return_value = mock_response

    # Test by passing keys directly as the function expects
    results = await web_search("test query", api_key="fake_key", cx_id="fake_cx")
    assert "Result 1" in results
    assert "https://example.com/2" in results


@patch("urllib.request.urlopen")
@pytest.mark.asyncio
async def test_web_fetch_html_cleaning(mock_url_open, mock_html_page):
    """Verifies that web_fetch strips tags and scripts correctly."""
    mock_response = MagicMock()
    mock_response.read.return_value = mock_html_page
    # Mock response.headers.get('Content-Type', '').lower()
    mock_response.headers.get.side_effect = lambda k, d="": "text/html" if k == "Content-Type" else d
    mock_response.__enter__.return_value = mock_response
    mock_url_open.return_value = mock_response

    content = await web_fetch("https://example.com")
    assert "Main Title" in content
    assert "Actual content here." in content
    assert "script" not in content.lower()
    assert "style" not in content.lower()


@pytest.mark.asyncio
async def test_web_fetch_truncation():
    """Verifies that content is truncated to the safety limit."""
    long_text = "A" * 5000
    # Simulate a response with long text
    with patch("urllib.request.urlopen") as mock_url_open:
        mock_response = MagicMock()
        mock_response.read.return_value = long_text.encode("utf-8")
        mock_response.headers.get.side_effect = lambda k, d="": "text/plain" if k == "Content-Type" else d
        mock_response.__enter__.return_value = mock_response
        mock_url_open.return_value = mock_response

        content = await web_fetch("https://example.com")
        assert len(content) <= 4100  # 4000 + notice
        assert "CONTENIDO TRUNCADO" in content


@patch("askgem.tools.web_tools.socket.getaddrinfo")
def test_is_safe_url_unsafe(mock_getaddrinfo):
    """Verifies that is_safe_url rejects private/loopback/non-global IPs."""
    # Mock loopback IP
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
    assert is_safe_url("http://localhost") is False
    assert is_safe_url("http://127.0.0.1") is False

    # Mock private IP
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 80))]
    assert is_safe_url("http://192.168.1.1") is False

    # Mock link-local IP
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 80))]
    assert is_safe_url("http://169.254.169.254") is False

    # Invalid schemes
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("ftp://example.com") is False


@patch("askgem.tools.web_tools.socket.getaddrinfo")
def test_is_safe_url_safe(mock_getaddrinfo):
    """Verifies that is_safe_url accepts global IPs."""
    # Mock global IP
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 80))]
    assert is_safe_url("https://google.com") is True


@patch("askgem.tools.web_tools.is_safe_url")
def test_web_fetch_ssrf_prevention(mock_is_safe_url):
    """Verifies that web_fetch rejects unsafe URLs."""
    mock_is_safe_url.return_value = False
    content = asyncio.run(web_fetch("http://localhost"))
    assert "Error: URL 'http://localhost' is invalid or blocked for security reasons." in content


@patch("src.askgem.tools.web_tools.socket.getaddrinfo")
def test_is_safe_url_edge_cases(mock_getaddrinfo):
    """Tests edge cases for SSRF protection."""
    # DNS rebinding attempt (hostname resolves to private IP)
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))]
    assert is_safe_url("http://evil.com") is False

    # IPv6 localhost
    mock_getaddrinfo.return_value = [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 80, 0, 0))]
    assert is_safe_url("http://[::1]") is False

    # IPv6 link-local
    mock_getaddrinfo.return_value = [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("fe80::1", 80, 0, 0))]
    assert is_safe_url("http://[fe80::1]") is False

    # URL with port
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 8080))]
    assert is_safe_url("http://10.0.0.1:8080") is False

    # Valid global IPv6
    mock_getaddrinfo.return_value = [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:4860:4860::8888", 80, 0, 0))]
    assert is_safe_url("http://[2001:4860:4860::8888]") is True
