import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import json
import os
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive"
}

def get_sports_links_from_main():
    """从新浪体育主页获取新闻链接"""
    try:
        print("🔍 正在访问新浪体育主页...")
        resp = requests.get("https://sports.sina.com.cn/", headers=headers, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        
        links = []
        all_links = soup.find_all("a", href=True)
        print(f"📄 主页总链接数: {len(all_links)}")
        
        for link in all_links:
            href = link.get("href", "")
            text = link.get_text(strip=True)
            
            # 处理相对链接
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://sports.sina.com.cn" + href
            
            # 筛选体育新闻链接
            if ("sports.sina.com.cn" in href and 
                (".shtml" in href or "/news/" in href or "/others/" in href or "/china/" in href) and
                text and len(text) > 5):
                links.append((href, text))
        
        # 去重
        unique_links = list(set(links))
        print(f"✅ 从主页找到 {len(unique_links)} 个体育新闻链接")
        
        return unique_links[:50]  # 限制数量避免过多
        
    except Exception as e:
        print(f"❌ 获取主页链接失败: {e}")
        return []

def get_sports_links_from_api():
    """尝试从新浪体育API获取新闻"""
    api_urls = [
        "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&k=&num=20&page=1",
        "https://sports.sina.com.cn/iframe/news_list.html",
        "https://roll.news.sina.com.cn/interface/rollnews_ch_out_interface.php?col=89&spec=&type=&ch=03&k=&offset_page=0&offset_num=0&num=20&asc=&page=1"
    ]
    
    links = []
    for api_url in api_urls:
        try:
            print(f"🔍 尝试API: {api_url}")
            resp = requests.get(api_url, headers=headers, timeout=10)
            
            if "json" in resp.headers.get("content-type", "").lower():
                # JSON响应
                data = resp.json()
                if "result" in data and "data" in data["result"]:
                    for item in data["result"]["data"][:20]:
                        if "url" in item and "title" in item:
                            links.append((item["url"], item["title"]))
            else:
                # HTML响应
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a.get("href")
                    text = a.get_text(strip=True)
                    if href and text and "sports.sina.com.cn" in href:
                        if href.startswith("//"):
                            href = "https:" + href
                        elif href.startswith("/"):
                            href = "https://sports.sina.com.cn" + href
                        links.append((href, text))
            
            if links:
                print(f"✅ API返回 {len(links)} 个链接")
                break
                
        except Exception as e:
            print(f"⚠️ API {api_url} 失败: {e}")
            continue
    
    return links[:30]

def get_sample_sports_articles():
    """获取一些固定的体育新闻样本"""
    # 这些是一些常见的体育新闻分类页面
    category_urls = [
        "https://sports.sina.com.cn/china/",
        "https://sports.sina.com.cn/csl/",
        "https://sports.sina.com.cn/basketball/",
        "https://sports.sina.com.cn/tennis/",
        "https://sports.sina.com.cn/others/"
    ]
    
    links = []
    for url in category_urls:
        try:
            print(f"🔍 访问分类页: {url}")
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 寻找新闻链接
            for a in soup.find_all("a", href=True):
                href = a.get("href")
                text = a.get_text(strip=True)
                
                if href and text and len(text) > 8:
                    # 处理相对链接
                    if href.startswith("//"):
                        href = "https:" + href
                    elif href.startswith("/"):
                        href = "https://sports.sina.com.cn" + href
                    
                    # 只要体育相关且是详情页
                    if ("sports.sina.com.cn" in href and 
                        ".shtml" in href and
                        not href.endswith("/") and
                        len(text.strip()) > 5):
                        links.append((href, text.strip()))
            
            time.sleep(1)  # 避免请求过快
            
        except Exception as e:
            print(f"⚠️ 访问分类页失败 {url}: {e}")
    
    # 去重并限制数量
    unique_links = list(set(links))
    print(f"✅ 从分类页找到 {len(unique_links)} 个新闻链接")
    return unique_links[:40]

def get_article_content(url, title_hint=""):
    """爬取文章内容"""
    try:
        print(f"📖 正在爬取: {title_hint[:30]}...")
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 多种标题选择器
        title = title_hint  # 使用链接文本作为默认标题
        title_selectors = [
            "h1.main-title", 
            "h1", 
            ".article-title h1",
            ".art-title h1",
            "title"
        ]
        
        for selector in title_selectors:
            elem = soup.select_one(selector)
            if elem and elem.get_text(strip=True):
                title = elem.get_text(strip=True)
                break
        
        # 多种内容选择器
        content = ""
        content_selectors = [
            ".art-content p",
            "#artibody p", 
            ".article-content p",
            ".content p",
            "div.content p",
            ".art-text p",
            "p"
        ]
        
        for selector in content_selectors:
            paragraphs = soup.select(selector)
            if paragraphs and len(paragraphs) > 2:  # 至少要有几段内容
                texts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    # 过滤掉明显的导航、广告等文本
                    if (text and len(text) > 10 and 
                        "新浪" not in text and "广告" not in text and 
                        "点击" not in text and "更多" not in text):
                        texts.append(text)
                
                if len(texts) >= 3:  # 至少3段有效内容
                    content = "\n".join(texts)
                    break
        
        # 如果还是没有内容，尝试获取所有文本
        if not content or len(content) < 100:
            # 移除脚本和样式
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
            
            # 获取主要内容区域的文本
            main_content = soup.find("div", class_=re.compile(r"(content|article|main)"))
            if main_content:
                content = main_content.get_text(strip=True, separator="\n")
        
        # 清理内容
        if content:
            lines = content.split("\n")
            clean_lines = []
            for line in lines:
                line = line.strip()
                if (line and len(line) > 10 and 
                    not line.startswith("新浪") and
                    "广告" not in line and "点击" not in line):
                    clean_lines.append(line)
            content = "\n".join(clean_lines)
        
        print(f"📝 标题: {title[:50]}...")
        print(f"📝 内容长度: {len(content)} 字符")
        
        return title, content
        
    except Exception as e:
        print(f"❌ 爬取失败 {url}: {e}")
        return None, None

def crawl_sports_news(max_articles=20, save_file="sports_news.csv"):
    """爬取体育新闻"""
    os.makedirs(os.path.dirname(save_file) if os.path.dirname(save_file) else ".", exist_ok=True)
    
    # 获取链接
    print("🚀 开始获取体育新闻链接...")
    all_links = []
    
    # 方法1: 主页链接
    main_links = get_sports_links_from_main()
    all_links.extend(main_links)
    
    # 方法2: API链接
    api_links = get_sports_links_from_api()
    all_links.extend(api_links)
    
    # 方法3: 分类页链接
    category_links = get_sample_sports_articles()
    all_links.extend(category_links)
    
    # 去重
    unique_links = list(set(all_links))
    print(f"📊 总共获得 {len(unique_links)} 个唯一链接")
    
    if not unique_links:
        print("❌ 没有找到任何体育新闻链接")
        return
    
    # 爬取文章内容
    success_count = 0
    with open(save_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "content", "url"])
        
        for i, (url, link_text) in enumerate(unique_links[:max_articles]):
            print(f"\n🔄 处理第 {i+1}/{min(len(unique_links), max_articles)} 篇文章...")
            
            title, content = get_article_content(url, link_text)
            
            if title and content and len(content.strip()) > 200:
                writer.writerow([title, content, url])
                success_count += 1
                print(f"✅ 成功保存: {title[:40]}...")
            else:
                print(f"⚠️ 跳过无效内容: {url}")
            
            # 随机延迟
            delay = random.uniform(2, 4)
            print(f"⏳ 等待 {delay:.1f} 秒...")
            time.sleep(delay)
    
    print(f"\n🎉 爬取完成！")
    print(f"📊 成功保存 {success_count} 篇文章到 {save_file}")
    return success_count

def convert_to_jsonl(csv_file="sports_news.csv", jsonl_file="data/sports.jsonl"):
    """转换为JSONL格式"""
    if not os.path.exists(csv_file):
        print(f"❌ CSV文件不存在: {csv_file}")
        return
    
    os.makedirs(os.path.dirname(jsonl_file) if os.path.dirname(jsonl_file) else ".", exist_ok=True)
    
    with open(csv_file, "r", encoding="utf-8") as f_in, \
         open(jsonl_file, "w", encoding="utf-8") as f_out:
        
        reader = csv.DictReader(f_in)
        count = 0
        
        for row in reader:
            record = {
                "统一发布平台unid": f"sports:{count+1}",
                "服务事项": f"体育新闻报道：{row['title']}",
                "权力类型": "新闻报道",
                "行驶主体": "新浪体育",
                "承办机构": "新浪网体育频道",
                "实施依据": row['url'],
                "责任事项": row['content'][:800] + "..." if len(row['content']) > 800 else row['content'],
                "监管电话": ""
            }
            
            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    
    print(f"✅ 已转换 {count} 条记录到 {jsonl_file}")

if __name__ == "__main__":
    print("🚀 开始爬取新浪体育新闻...")
    
    success_count = crawl_sports_news(max_articles=15, save_file="scripts/sports_news.csv")
    
    if success_count > 0:
        convert_to_jsonl("scripts/sports_news.csv", "data/sports.jsonl")
        print(f"🎉 成功爬取并转换了 {success_count} 篇体育新闻！")
    else:
        print("❌ 没有成功爬取到任何文章")
