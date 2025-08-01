# -------------- USED LATER --------------#

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36    (KHTML, like Gecko) "
                  "Chrome/102.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def search_google(query):
    url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if "Our systems have detected unusual traffic" in response.text:
            return None  # fallback trigger

        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for g in soup.select("div.g"):
            title_tag = g.select_one("h3")
            link_tag = g.select_one("a")
            snippet_tag = g.select_one("div.IsZvec")

            if title_tag and link_tag:
                results.append({
                    "title": title_tag.text.strip(),
                    "url": link_tag.get("href"),
                    "snippet": snippet_tag.text.strip() if snippet_tag else ""
                })
        return results if results else None
    except Exception:
        return None

def search_duckduckgo(query):
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        response = requests.post(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        for result in soup.select(".result"):
            link_tag = result.select_one("a")
            snippet_tag = result.select_one(".result__snippet")
            if link_tag:
                results.append({
                    "title": link_tag.text.strip(),
                    "url": link_tag.get("href"),
                    "snippet": snippet_tag.text.strip() if snippet_tag else ""
                })
        return results if results else None
    except Exception:
        return None

def hybrid_search(query):
    results = search_google(query)
    engine = "Google"
    if results is None:
        results = search_duckduckgo(query)
        engine = "DuckDuckGo" if results else "None"
    return results or [], engine

