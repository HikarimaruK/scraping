import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import os
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import time as pytime
from urllib.parse import urljoin

def get_user_agent():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 従来のheadlessで安定化
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument(f'user-agent={get_user_agent()}')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    return driver

def fetch_list_page(url: str, use_selenium: bool = True, driver=None) -> Optional[str]:
    """一覧ページのHTMLを取得。まずrequestsで試し、失敗時のみSeleniumにフォールバック"""
    html = None
    # まずrequestsで取得
    try:
        headers = {"User-Agent": get_user_agent()}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
    except Exception as e:
        html = None
    # requestsで失敗した場合のみSelenium
    if not html and use_selenium:
        try:
            if driver is None:
                driver = create_driver()
                close_driver = True
            else:
                close_driver = False
            driver.get(url)
            pytime.sleep(2 + random.uniform(1, 2))
            html = driver.page_source
            if close_driver:
                driver.quit()
        except Exception as e:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            html = None
    # デバッグ用: 取得できたHTMLの先頭200文字を出力
    if html:
        print("[DEBUG] HTML取得成功: ", html[:200])
    else:
        print("[DEBUG] HTML取得失敗: ", url)
    return html

def extract_detail_urls(list_html: str, detail_selector: str, base_url: str = "") -> List[str]:
    soup = BeautifulSoup(list_html, "lxml")
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

def fetch_detail_page(url: str, use_selenium: bool = True, driver=None) -> Optional[str]:
    """詳細ページのHTMLを取得。まずrequestsで試し、失敗時のみSeleniumにフォールバック"""
    html = None
    try:
        headers = {"User-Agent": get_user_agent()}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
    except Exception as e:
        html = None
    if not html and use_selenium:
        try:
            if driver is None:
                driver = create_driver()
                close_driver = True
            else:
                close_driver = False
            driver.get(url)
            pytime.sleep(2 + random.uniform(1, 2))
            html = driver.page_source
            if close_driver:
                driver.quit()
        except Exception as e:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
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
    # ドライバーを1つだけ生成して使い回す
    driver = create_driver()
    html = fetch_list_page(list_url, use_selenium=True, driver=driver)
    if html:
        detail_urls = extract_detail_urls(html, detail_selector, base_url="https://www.daijob.com")
        for url in detail_urls[:1]:
            d_html = fetch_detail_page(url, use_selenium=True, driver=driver)
            if d_html:
                print(extract_elements(d_html, selectors))
            pytime.sleep(2 + random.uniform(1, 2))  # 2～4秒ランダムスリープ
    driver.quit()
