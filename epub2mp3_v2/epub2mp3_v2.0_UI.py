import os
import re
import zipfile
import asyncio
import time
from bs4 import BeautifulSoup
import edge_tts

# 引入 Windows 原生图形界面库
import tkinter as tk
from tkinter import filedialog, messagebox

# ==================== 默认配置 ====================
VOICE_ACTOR = "en-GB-SoniaNeural" 
OUTPUT_FOLDER = "Economist_Audio_Tracks"
# ==================================================

def sanitize_filename(filename):
    filename = re.sub(r'[\/*?:"<>|]', "", filename)
    filename = filename.strip().replace(" ", "_")
    return filename[:50]

def violence_scan_epub(epub_path, log_widget):
    log_widget.insert(tk.END, "🔓 正在启动暴力解压扫描（ZIP Full Scan）...\n")
    log_widget.see(tk.END)
    log_widget.update()
    
    chapters = []
    track_num = 1
    
    with zipfile.ZipFile(epub_path, 'r') as z:
        for file_name in z.namelist():
            if file_name.endswith(('.html', '.xhtml', '.htm')):
                html_content = z.read(file_name)
                soup = BeautifulSoup(html_content, 'html.parser', from_encoding='utf-8')
                
                paragraphs = soup.find_all('p')
                article_text = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                
                if len(article_text) < 150:
                    continue
                
                title_tag = soup.find(['h1', 'h2', 'h3'])
                if title_tag and len(title_tag.get_text().strip()) > 2:
                    title_text = title_tag.get_text().strip()
                else:
                    first_line = article_text.split('\n')
                    title_text = first_line[:30] + "..." if len(first_line) > 30 else first_line
                
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

async def convert_single_track(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

async def process_all_chapters(chapters, base_dir, log_widget, metrics_label):
    output_path = os.path.join(base_dir, OUTPUT_FOLDER)
    if not os.path.exists(output_path):
        os.makedirs(output_path)
        
    log_widget.insert(tk.END, f"\n🚀 扫描成功！共发现 {len(chapters)} 篇文章。开始调用云端进行转换...\n")
    log_widget.see(tk.END)
    
    # ⏱️ 开启总计时器
    start_time = time.time()
    total_bytes = 0 # 用于累加计算总流量
    
    for index, chapter in enumerate(chapters):
        file_path = os.path.join(output_path, chapter["filename"])
        log_widget.insert(tk.END, f"🎙️ [{index+1}/{len(chapters)}] 正在转换: {chapter['title'][:25]}...\n")
        log_widget.see(tk.END)
        log_widget.update()
        
        try:
            # 调用微软云
            await convert_single_track(chapter["text"], VOICE_ACTOR, file_path)
            
            # 📊 流量统计核心：转换成功后，立刻读取该 MP3 文件的物理大小（字节）
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                total_bytes += file_size
                
        except Exception as e:
            log_widget.insert(tk.END, f"❌ 失败: {chapter['title'][:10]}... 原因: {e}\n")
            
    # ⏱️ 结束总计时
    end_time = time.time()
    total_seconds = end_time - start_time
    
    # 时间度量计算
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    avg_seconds = total_seconds / len(chapters) if chapters else 0
    
    # 流量度量计算 (1 MB = 1024 * 1024 字节)
    total_mb = total_bytes / (1024 * 1024)
    
    log_widget.insert(tk.END, f"\n✨ ✨ 恭喜！全刊分轨转换全部完成！\n")
    log_widget.see(tk.END)
    
    # 🎯 核心改进：在界面的专用 Metrics 仪表盘区域刷新显示数据
    metrics_report = (
        f"📊 [云端度量报告]\n"
        f"⏱️ 总计用时: {minutes} 分 {seconds} 秒\n"
        f"⚡ 平均耗时: {avg_seconds:.2f} 秒/篇\n"
        f"🌐 流量消费: {total_mb:.2f} MB"
    )
    metrics_label.config(text=metrics_report)
    messagebox.showinfo("成功", "全刊分轨音频转换及云端统计已完成！")

def start_conversion(epub_path, log_widget, metrics_label, start_btn):
    if not epub_path:
        messagebox.showwarning("警告", "请先选择一个 EPUB 文件！")
        return
        
    start_btn.config(state=tk.DISABLED)
    base_dir = os.path.dirname(epub_path)
    
    try:
        all_articles = violence_scan_epub(epub_path, log_widget)
        if not all_articles:
            messagebox.showerror("错误", "该电子书内未提取到有效正文文本。")
            start_btn.config(state=tk.NORMAL)
            return
            
        asyncio.run(process_all_chapters(all_articles, base_dir, log_widget, metrics_label))
    except Exception as e:
        log_widget.insert(tk.END, f"\n❌ 程序运行时崩溃: {e}\n")
    finally:
        start_btn.config(state=tk.NORMAL)

def create_gui():
    """使用 tkinter 构建可视化窗口"""
    root = tk.Tk()
    root.title("经济学人音频转换与云度量监控面板 v1.0")
    root.geometry("650x550")
    root.config(bg="#F5F5F5")
    
    selected_path = tk.StringVar()
    
    # 1. 第一栏：文件选择区域
    lbl_file = tk.Label(root, text="第一栏：输入/选择 EPUB 电子书路径", font=("Segoe UI", 10, "bold"), bg="#F5F5F5", anchor="w")
    lbl_file.pack(fill=tk.X, padx=15, pady=(15, 2))
    
    file_frame = tk.Frame(root, bg="#F5F5F5")
    file_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
    
    entry = tk.Entry(file_frame, textvariable=selected_path, font=("Segoe UI", 10), bd=2, relief=tk.GROOVE)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))
    
    def select_file():
        file_path = filedialog.askopenfilename(title="选择经济学人 EPUB 电子书", filetypes=[("EPUB Files", "*.epub")])
        if file_path:
            selected_path.set(file_path)
            
    btn_browse = tk.Button(file_frame, text="浏览文件", command=select_file, bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold"), padx=10)
    btn_browse.pack(side=tk.RIGHT)
    
    # 2. 第二栏：云端度量显示面板（仪表盘区域）
    lbl_metrics = tk.Label(root, text="第二栏：时延与云端流量消费监控 (Metrics)", font=("Segoe UI", 10, "bold"), bg="#F5F5F5", anchor="w")
    lbl_metrics.pack(fill=tk.X, padx=15, pady=(10, 2))
    
    # 仪表盘框架
    metrics_frame = tk.LabelFrame(root, text=" 实时云端仪表盘 ", font=("Segoe UI", 9), bg="#E3F2FD", fg="#0D47A1", bd=2, relief=tk.SOLID)
    metrics_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
    
    metrics_display = (
        "📊 [云端度量报告]\n"
        "⏱️ 总计用时: -- 分 -- 秒\n"
        "⚡ 平均耗时: -- 秒/篇\n"
        "🌐 流量消费: -- MB"
    )
    lbl_metrics_data = tk.Label(metrics_frame, text=metrics_display, font=("Consolas", 11, "bold"), bg="#E3F2FD", fg="#1565C0", justify=tk.LEFT, anchor="w", padx=15, pady=10)
    lbl_metrics_data.pack(fill=tk.X)
    
    # 3. 中间：实时运行状态日志
    lbl_log = tk.Label(root, text="第三栏：流水线执行日志 (Logs)", font=("Segoe UI", 10, "bold"), bg="#F5F5F5", anchor="w")
    lbl_log.pack(fill=tk.X, padx=15, pady=(0, 2))
    
    log_frame = tk.Frame(root)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
    
    scrollbar = tk.Scrollbar(log_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    log_text = tk.Text(log_frame, yscrollcommand=scrollbar.set, bg="#1E1E1E", fg="#A9B7C6", font=("Consolas", 10))
    log_text.pack(fill=tk.BOTH, expand=True)
    scrollbar.config(command=log_text.yview)
    
    # 4. 底部执行按钮
    btn_start = tk.Button(root, text="🚀 启动自动化云端转换流水线", 
                          command=lambda: start_conversion(selected_path.get(), log_text, lbl_metrics_data, btn_start),
                          bg="#4CAF50", fg="white", font=("Segoe UI", 11, "bold"), pady=8)
    btn_start.pack(fill=tk.X, padx=15, pady=(0, 15))
    
    log_text.insert(tk.END, "💡 使用向导：\n1. 点击第一栏的【浏览文件】选择本周的《经济学人》EPUB 电子书。\n2. 点击底部绿色按钮启动。转换完成后，第二栏的仪表盘将自动清算本次任务的总用时、平均每篇耗时及消耗的 Wi-Fi 流量。\n------------------------------------------------------------\n")
    
    root.mainloop()

if __name__ == "__main__":
    create_gui()

print("\n" + "=" * 30)
input("按【回车键 (Enter)】退出程序...") 