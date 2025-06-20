import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

def fetch_list_page(url: str) -> Optional[str]:
    """一覧ページのHTMLを取得"""
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.text
    except Exception as e:
        return None

def extract_detail_urls(list_html: str, detail_selector: str, base_url: str = "") -> List[str]:
    """一覧ページHTMLから詳細ページURLを抽出"""
    soup = BeautifulSoup(list_html, "lxml")
    links = []
    for tag in soup.select(detail_selector):
        href = tag.get("href")
        if href:
            # 相対パス対応
            if href.startswith("http"):
                links.append(href)
            else:
                links.append(base_url.rstrip("/") + "/" + href.lstrip("/"))
    return links

def fetch_detail_page(url: str) -> Optional[str]:
    """詳細ページのHTMLを取得"""
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.text
    except Exception as e:
        return None

def extract_elements(detail_html: str, selectors: List[Dict[str, str]]) -> Dict[str, str]:
    """
    詳細ページHTMLから要素を抽出
    selectors: [{"name": "タイトル", "selector": "h1.title", "type": "css"}, ...]
    """
    soup = BeautifulSoup(detail_html, "lxml")
    result = {}
    for sel in selectors:
        name = sel["name"]
        selector = sel["selector"]
        sel_type = sel.get("type", "css")
        if sel_type == "css":
            el = soup.select_one(selector)
            result[name] = el.get_text(strip=True) if el else ""
        # XPath対応は将来的な拡張で
        # elif sel_type == "xpath":
        #     pass
    return result

# --- サンプルテストコード ---
if __name__ == "__main__":
    # サンプル: Qiitaのタグページから記事タイトルを抽出
    list_url = "https://qiita.com/tags/python?page=1"
    detail_selector = "h2 > a"
    selectors = [
        {"name": "タイトル", "selector": "h1", "type": "css"},
    ]
    html = fetch_list_page(list_url)
    if html:
        detail_urls = extract_detail_urls(html, detail_selector, base_url="https://qiita.com")
        for url in detail_urls[:1]:
            d_html = fetch_detail_page(url)
            if d_html:
                print(extract_elements(d_html, selectors))
