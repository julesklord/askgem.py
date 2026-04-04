import asyncio
import json
import re
import urllib.parse
import urllib.request
from typing import Optional

# Pre-compiled regex patterns for performance
RE_DDG_RESULTS = re.compile(
    r'<a class="result__a" href="([^"]+)">([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]+)</a>',
    re.DOTALL,
)
RE_SCRIPT_STYLE = re.compile(r"<(script|style).*?>.*?</\1>", re.DOTALL | re.IGNORECASE)
RE_HTML_TAGS = re.compile(r"<.*?>", re.DOTALL)
RE_MULTIPLE_NEWLINES = re.compile(r"\n\s*\n")
RE_MULTIPLE_SPACES = re.compile(r" +")


async def web_search(query: str, api_key: Optional[str] = None, cx_id: Optional[str] = None) -> str:
    """
    Search the web using Google Custom Search (if keys provided) or DuckDuckGo (fallback).
    Returns a formatted string of results.
    """
    if api_key and cx_id:
        return await _google_search(query, api_key, cx_id)
    else:
        return await _duckduckgo_search(query)


def _google_search(query: str, api_key: str, cx_id: str) -> str:
    try:
        safe_query = urllib.parse.quote(query)
        url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx_id}&q={safe_query}"

        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.load(response)
            items = data.get("items", [])

            if not items:
                return "No se encontraron resultados en Google."

        results = ["[RESULTADOS DE BÚSQUEDA (GOOGLE)]"]
        for i, item in enumerate(items[:5], 1):
            results.append(f"{i}. {item['title']}")
            results.append(f"   URL: {item['link']}")
            results.append(f"   Snippet: {item.get('snippet', '')}\n")

        return "\n".join(results)
    except Exception as e:
        return f"Error en búsqueda de Google: {str(e)}. Intentando fallback..."


def _duckduckgo_search(query: str) -> str:
    """Zero-config search fallback using DuckDuckGo HTML interface."""
    try:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        safe_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={safe_query}"

        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")

        # Simple regex to extract results (titles and snippets)
        # This is a bit fragile but works for a lite fallback
        results = ["[RESULTADOS DE BÚSQUEDA (DUCKDUCKGO)]"]

        # Find result blocks
        matches = RE_DDG_RESULTS.finditer(html)

        count = 0
        for match in matches:
            if count >= 5:
                break
            link, title, snippet = match.groups()
            # Clean up title (it might have HTML entities)
            title = title.strip().replace("&amp;", "&")
            results.append(f"{count + 1}. {title}")
            results.append(f"   URL: {link}")
            results.append(f"   Snippet: {snippet.strip()}\n")
            count += 1

        if count == 0:
            return "No se encontraron resultados en DuckDuckGo. Por favor revisa tu conexión o intenta con otra consulta."

        return "\n".join(results)
    except Exception as e:
        return f"Error en búsqueda de DuckDuckGo: {str(e)}"


def web_fetch(url: str) -> str:
    """Fetches a URL and returns cleaned text content."""
    try:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})

        with urllib.request.urlopen(req, timeout=10) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if (
                "text/html" not in content_type
                and "text/plain" not in content_type
                and "application/json" not in content_type
            ):
                return f"Error: No se puede leer contenido de tipo {content_type}."

            content = response.read().decode("utf-8", errors="ignore")

        if "text/html" in content_type:
            # Strip script and style tags completely
            content = RE_SCRIPT_STYLE.sub("", content)
            # Strip all other HTML tags
            content = RE_HTML_TAGS.sub("", content)
            # Normalize whitespace
            content = RE_MULTIPLE_NEWLINES.sub("\n\n", content)
            content = RE_MULTIPLE_SPACES.sub(" ", content)
            content = content.strip()

        # Truncate to avoid token explosion (Milestone 3 spec: 4000 chars)
        if len(content) > 4000:
            return content[:4000] + "\n\n[CONTENIDO TRUNCADO POR LÍMITE DE 4000 CARACTERES]"

        return content

    except Exception as e:
        return f"Error al leer URL {url}: {str(e)}"
