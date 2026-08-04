import os
import re
import requests
from playwright.sync_api import sync_playwright

# 1. 目标播客列表网页
url = "https://www.economist.com/podcasts/2026/08/01/the-war-on-animal-research"

# 用一个集合来记录已经下载过的链接，防止重复下载同一个音频
downloaded_urls = set()

def download_audio(mp3_url):
    """负责将抓取到的特定 MP3 链接下载到本地"""
    if mp3_url in downloaded_urls:
        return # 如果已经下载过，跳过
        
    downloaded_urls.add(mp3_url)
    print(f"\n🎵 [截获音频链接]: {mp3_url}")
    
    # 2. 自动提取一个好记的文件名
    # 经济学人播客链接通常包含日期，例如 .../20260801_intelligence.mp3
    # 我们用正则表达式提取最后一段作为文件名
    match = re.search(r'([^/]+\.mp3)', mp3_url.split('?')[0])
    filename = match.group(1) if match else "economist_podcast.mp3"
    
    print(f"📥 开始下载: {filename} ...")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(mp3_url, headers=headers, timeout=30)
        
        with open(filename, "wb") as f:
            f.write(response.content)
            
        print(f"✨ 成功保存至本地: {filename}")
        print("👉 你可以继续在网页上点击其他音频进行下载，或者直接关闭浏览器退出。")
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        if mp3_url in downloaded_urls:
            downloaded_urls.remove(mp3_url) # 失败了允许重试

def main():
    with sync_playwright() as p:
        # 保持 headless=False，因为你需要手动挑选点击
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # 核心：持续监听网络请求，只要符合条件就去下载，不终止程序
        page.on("response", lambda response: download_audio(response.url) if ".mp3" in response.url else None)

        print("正在打开经济学人播客页面...")
        page.goto(url, wait_until="domcontentloaded")

        print("\n📢 ====== 使用说明 ======")
        print("1. 请在弹出的浏览器窗口中，找到你想听的那一期节目。")
        print("2. 点击它的【Play（播放）】按钮。")
        print("3. 只要后台开始加载该音频，命令行就会显示下载进度。")
        print("4. 下载完成后，你可以【继续点击下一首】。")
        print("5. 全部下载完成后，直接【关闭弹出的浏览器窗口】即可结束程序。")
        print("=========================\n")

        # 让浏览器保持打开状态，给你足够的时间去挑选和播放（设置为等待 10 分钟）
        page.wait_for_timeout(600000)
        browser.close()

if __name__ == "__main__":
    main()
    
    print("\n" + "=" * 30)
    input("按【回车键 (Enter)】退出程序...")