import os
import re
import zipfile
import asyncio
from bs4 import BeautifulSoup
import edge_tts

# ==================== 配置区域 ====================
EPUB_FILE_PATH = "The_Economist_2026_08_01.epub" # 👈 请确保和你的文件名一致
VOICE_ACTOR = "en-GB-SoniaNeural" 
OUTPUT_FOLDER = "Economist_Audio_Tracks"
# ==================================================

def sanitize_filename(filename):
    """清理文件名，去除系统不允许的特殊字符"""
    filename = re.sub(r'[\/*?:"<>|]', "", filename)
    filename = filename.strip().replace(" ", "_")
    return filename[:50]

def violence_scan_epub(epub_path):
    """降维打击逻辑：直接把 EPUB 当成 ZIP 解压，全面搜刮所有网页文件"""
    print("🔓 正在启动暴力解压扫描（ZIP Full Scan）...")
    chapters = []
    track_num = 1
    
    if not zipfile.is_zipfile(epub_path):
        print("❌ 错误：该文件似乎不是一个标准的 EPUB/ZIP 压缩包。")
        return []

    with zipfile.ZipFile(epub_path, 'r') as z:
        # 遍历压缩包里的每一个子文件
        for file_name in z.namelist():
            # 只要是包含文本的网页文件（忽略样式表和图片）
            if file_name.endswith(('.html', '.xhtml', '.htm')):
                html_content = z.read(file_name)
                # 使用 BeautifulSoup 强行解析纯文本
                soup = BeautifulSoup(html_content, 'html.parser', from_encoding='utf-8')
                
                # 提取纯文本段落
                paragraphs = soup.find_all('p')
                article_text = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                
                # 💡 降低门槛：只要字数大于 150 个字，就认定是一篇文章
                if len(article_text) < 150:
                    continue
                
                # 智能寻找标题
                title_tag = soup.find(['h1', 'h2', 'h3'])
                if title_tag and len(title_tag.get_text().strip()) > 2:
                    title_text = title_tag.get_text().strip()
                else:
                    # 如果找不到标签标题，拿前 30 个字当标题
                    first_line = article_text.split('\n')[0]
                    title_text = first_line[:30] + "..." if len(first_line) > 30 else first_line
                
                # 过滤掉无意义的管理页面
                if "contents" in title_text.lower() or "index" in title_text.lower() or "cover" in title_text.lower():
                    continue
                
                safe_title = sanitize_filename(title_text)
                filename = f"{track_num:02d}_{safe_title}.mp3"
                full_reading_text = f"Article {track_num}. {title_text}.\n\n{article_text}"
                
                chapters.append({
                    "filename": filename,
                    "text": full_reading_text,
                    "title": title_text
                })
                track_num += 1
                
    return chapters

async def convert_single_track(text, voice, output_path, title):
    print(f"🎙️ 正在转换: 【{title}】...")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

async def process_all_chapters(chapters):
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        
    print(f"\n🚀 暴力扫描成功！共强行剥离出 {len(chapters)} 篇有效文章文本。开始生成音频...")
    
    for index, chapter in enumerate(chapters):
        file_path = os.path.join(OUTPUT_FOLDER, chapter["filename"])
        print(f"\n[进度 {index+1}/{len(chapters)}]")
        try:
            await convert_single_track(chapter["text"], VOICE_ACTOR, file_path, chapter["title"])
        except Exception as e:
            print(f"❌ 转换失败: {chapter['title']}，原因: {e}")
            
    print(f"\n✨ ✨ 恭喜！全刊分轨转换全部完成！")
    print(f"📁 音频文件夹路径: 【{os.path.abspath(OUTPUT_FOLDER)}】")

def main():
    try:
        if not os.path.exists(EPUB_FILE_PATH):
            print(f"❌ 错误：未找到文件 [{EPUB_FILE_PATH}]")
            return
            
        all_articles = violence_scan_epub(EPUB_FILE_PATH)
        if not all_articles:
            print("❌ 降维打击依然无果，说明该电子书内可能确实全被加密锁死或纯为图片。")
            return
            
        asyncio.run(process_all_chapters(all_articles))
        
    except Exception as e:
        print(f"\n❌ 程序运行时崩溃: {e}")
        
    finally:
        print("\n" + "=" * 30)
        input("按【回车键 (Enter)】退出程序...")

if __name__ == "__main__":
    main()