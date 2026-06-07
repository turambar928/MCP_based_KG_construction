import requests
from bs4 import BeautifulSoup
import time
import random
import csv

# 爬取的目标：新浪体育新闻
BASE_URL = "https://sports.sina.com.cn/"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

def get_article_links(page_url):
    """获取新闻列表页的文章链接"""
    resp = requests.get(page_url, headers=headers, timeout=10)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    links = []
    for a in soup.select("a"):
        href = a.get("href", "")
        if href.startswith("https://sports.sina.com.cn/"):
            if href.endswith(".shtml"):  # 只要新闻详情页
                links.append(href)
    return list(set(links))  # 去重


def get_article_content(url):
    """爬取单篇文章的标题和正文"""
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        title = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else "无标题"
        paragraphs = [p.get_text(strip=True) for p in soup.select("div#article p")]
        content = "\n".join(paragraphs)
        return title, content
    except Exception as e:
        print(f"❌ 爬取失败: {url}, 错误: {e}")
        return None, None


def crawl_sina_sports(start_page=1, end_page=3, save_file="sports_news.csv"):
    """批量爬取新浪体育新闻"""
    with open(save_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "content", "url"])  # CSV 表头

        for page in range(start_page, end_page + 1):
            print(f"📄 正在爬取第 {page} 页 ...")
            page_url = f"https://sports.sina.com.cn/roll/index.d.html?cid=0&pn={page}"
            links = get_article_links(page_url)

            for link in links:
                title, content = get_article_content(link)
                if content:
                    writer.writerow([title, content, link])
                    print(f"✅ {title[:20]}... 已保存")
                time.sleep(random.uniform(1, 3))  # 随机延迟，避免被封

    print(f"🎉 爬取完成，结果保存在 {save_file}")


if __name__ == "__main__":
    crawl_sina_sports(start_page=1, end_page=5)  # 爬取前 5 页
