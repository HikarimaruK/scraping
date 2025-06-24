import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import os
import random
import time as pytime
from urllib.parse import urljoin

def get_user_agent():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def fetch_list_page(url: str, use_selenium: bool = False, driver=None) -> Optional[str]:
    """一覧ページのHTMLを取得。requestsのみ（Seleniumは自動コメントアウト）"""
    html = None
    try:
        headers = {"User-Agent": get_user_agent()}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
    except Exception as e:
        html = None
    if html:
        print("[DEBUG] HTML取得成功: ", html[:200])
    else:
        print("[DEBUG] HTML取得失敗: ", url)
    return html

def extract_detail_urls(list_html: str, detail_selector: str, base_url: str = "") -> List[str]:
    # lxmlが使えない場合はhtml.parserでフォールバック
    try:
        soup = BeautifulSoup(list_html, "lxml")
    except Exception:
        soup = BeautifulSoup(list_html, "html.parser")
    links = []
    # まず指定セレクタでタグを取得
    tags = soup.select(detail_selector)
    for tag in tags:
        # aタグならそのままhrefを取得
        if tag.name == "a":
            href = tag.get("href")
            if href:
                links.append(urljoin(base_url, href))
        else:
            # aタグでなければ、子孫のaタグをすべて取得
            for a in tag.find_all("a", href=True):
                href = a.get("href")
                if href:
                    links.append(urljoin(base_url, href))
    return links

def fetch_detail_page(url: str, use_selenium: bool = False, driver=None) -> Optional[str]:
    """詳細ページのHTMLを取得。requestsのみ（Seleniumは自動コメントアウト）"""
    html = None
    try:
        headers = {"User-Agent": get_user_agent()}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
    except Exception as e:
        html = None
    if html:
        print("[DEBUG] 詳細HTML取得成功: ", html[:200])
    else:
        print("[DEBUG] 詳細HTML取得失敗: ", url)
    return html

def extract_elements(detail_html: str, selectors: List[Dict[str, str]]) -> Dict[str, str]:
    soup = BeautifulSoup(detail_html, "lxml")
    result = {}
    for sel in selectors:
        name = sel["name"]
        selector = sel["selector"]
        sel_type = sel.get("type", "css")
        if sel_type == "css":
            el = soup.select_one(selector)
            result[name] = el.get_text(strip=True) if el else ""
    return result

# --- サンプルテストコード ---
if __name__ == "__main__":
    list_url = "https://www.daijob.com/jobs/search_result?job_post_language=2&page=1"
    detail_selector = "#mdj_page > div.section01 > div:nth-child(2) > div.jobs_box_header > div.jobs_box_header_position.mb16 > h4"
    selectors = [
        {"name": "要素1", "selector": "#mdj_page > div.section01 > div > div.jobs_box_content > div > div > table > tbody > tr:nth-child(1) > td > h4", "type": "css"},
        {"name": "要素2", "selector": "#mdj_page > div.section01 > div > div.jobs_box_header > div.jobs_box_header_position.mb16 > h4 > span", "type": "css"},
    ]
    html = fetch_list_page(list_url, use_selenium=False)
    if html:
        detail_urls = extract_detail_urls(html, detail_selector, base_url="https://www.daijob.com")
        for url in detail_urls[:1]:
            d_html = fetch_detail_page(url, use_selenium=False)
            if d_html:
                print(extract_elements(d_html, selectors))
            pytime.sleep(2 + random.uniform(1, 2))  # 2～4秒ランダムスリープ
