import os, re, zipfile, asyncio, time
from bs4 import BeautifulSoup
import edge_tts
from pypdf import PdfReader
import tkinter as tk
from tkinter import filedialog, messagebox

VOICE_ACTOR = "en-GB-SoniaNeural"
OUTPUT_FOLDER = "Economist_Audio_Tracks"
is_stop_requested = False

def sanitize_filename(filename):
    return re.sub(r'[\/*?:"<>|]', "", filename).strip().replace(" ", "_").replace("\n", "")[:40]

def violence_scan_epub(epub_path, log_widget):
    log_widget.insert(tk.END, "🔓 正在启动 [EPUB] 暴力解压扫描流程...\n")
    log_widget.update()
    chapters, track_num = [], 1
    with zipfile.ZipFile(epub_path, 'r') as z:
        for file_name in z.namelist():
            if file_name.endswith(('.html', '.xhtml', '.htm')):
                soup = BeautifulSoup(z.read(file_name), 'html.parser', from_encoding='utf-8')
                paragraphs = soup.find_all('p')
                article_text = "\n".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                if len(article_text) < 150: continue
                title_tag = soup.find(['h1', 'h2', 'h3'])
                title_text = title_tag.get_text().strip() if title_tag else (article_text.split('\n')[0][:30] + "...")
                if "contents" in title_text.lower() or "index" in title_text.lower(): continue
                chapters.append({
                    "filename": f"{track_num:02d}_{sanitize_filename(title_text)}.mp3",
                    "text": f"Article {track_num}. {title_text}.\n\n{article_text}", "title": title_text
                })
                track_num += 1
    return chapters

def scan_and_extract_pdf(pdf_path, log_widget):
    log_widget.insert(tk.END, "📄 正在启动 [PDF] 物理页面智能分析流程...\n")
    log_widget.update()
    chapters = []
    reader = PdfReader(pdf_path)
    for index, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if not page_text or len(page_text.strip()) < 80: continue
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        if not lines: continue
        raw_title = lines[0] if len(lines) > 0 else f"Page_{index+1}"
        if len(raw_title) > 40: raw_title = raw_title[:35] + "..."
        chapters.append({
            "filename": f"{index+1:02d}_Page_{index+1:03d}_{sanitize_filename(raw_title)}.mp3",
            "text": f"Document Page {index+1}. Title: {raw_title}.\n\n" + "\n".join(lines),
            "title": f"第 {index+1} 页: {raw_title}"
        })
    return chapters

async def convert_single_track(text, voice, output_path):
    await edge_tts.Communicate(text, voice).save(output_path)

async def process_all_chapters(chapters, base_dir, log_widget, metrics_label):
    global is_stop_requested
    output_path = os.path.join(base_dir, OUTPUT_FOLDER)
    if not os.path.exists(output_path): os.makedirs(output_path)
    log_widget.insert(tk.END, f"\n🚀 引擎解析完成！共发现 {len(chapters)} 个有效分轨。开始下载语音...\n")
    
    start_time, total_bytes, success_count = time.time(), 0, 0
    for index, chapter in enumerate(chapters):
        if is_stop_requested:
            log_widget.insert(tk.END, "\n🛑 [熔断触发] 收到用户终止指令，正在清算数据...\n")
            break
        file_path = os.path.join(output_path, chapter["filename"])
        log_widget.insert(tk.END, f"🎙️ [{index+1}/{len(chapters)}] 正在转换: {chapter['title'][:25]}...\n")
        log_widget.see(tk.END); log_widget.update()
        try:
            await convert_single_track(chapter["text"], VOICE_ACTOR, file_path)
            if os.path.exists(file_path):
                total_bytes += os.path.getsize(file_path)
                success_count += 1
        except Exception as e:
            log_widget.insert(tk.END, f"❌ 失败: {chapter['title'][:10]}... 原因: {e}\n")
            
    total_seconds = time.time() - start_time
    minutes, seconds = int(total_seconds // 60), int(total_seconds % 60)
    avg_seconds = total_seconds / success_count if success_count else 0
    total_mb = total_bytes / (1024 * 1024)
    
    log_widget.insert(tk.END, f"\n✨ 流水线作业处理完毕。共成功转换 {success_count} 篇音频。\n")
    log_widget.see(tk.END)
    metrics_label.config(text=f"📊 [云端度量报告]\n⏱️ 实际运行: {minutes} 分 {seconds} 秒\n⚡ 平均耗时: {avg_seconds:.2f} 秒/篇\n🌐 流量消费: {total_mb:.2f} MB")
    messagebox.showwarning("提示", f"任务结束！已处理 {success_count} 首音频。") if is_stop_requested else messagebox.showinfo("成功", "全能分轨转换已全部完成！")

def stop_conversion(log_widget, stop_btn):
    global is_stop_requested
    is_stop_requested = True
    log_widget.insert(tk.END, "\n⏳ 正在向云端发送中断信号，当前单篇完成后将彻底停下...\n")
    log_widget.see(tk.END); stop_btn.config(state=tk.DISABLED)

def start_conversion(file_path, log_widget, metrics_label, start_btn, stop_btn):
    global is_stop_requested
    if not file_path:
        messagebox.showwarning("警告", "请先选择一个文件！")
        return
    is_stop_requested = False
    start_btn.config(state=tk.DISABLED); stop_btn.config(state=tk.NORMAL)
    base_dir = os.path.dirname(file_path)
    try:
        if file_path.lower().endswith('.epub'): all_articles = violence_scan_epub(file_path, log_widget)
        elif file_path.lower().endswith('.pdf'): all_articles = scan_and_extract_pdf(file_path, log_widget)
        else: return
        if not all_articles: return
        asyncio.run(process_all_chapters(all_articles, base_dir, log_widget, metrics_label))
    except Exception as e: log_widget.insert(tk.END, f"\n❌ 错误: {e}\n")
    finally: start_btn.config(state=tk.NORMAL); stop_btn.config(state=tk.DISABLED)

def create_gui():
    root = tk.Tk()
    root.title("全能外刊 AI 语音转换与故障熔断控制面板 v2.5")
    root.geometry("650x580")
    selected_path = tk.StringVar()
    
    tk.Label(root, text="第一栏：输入/选择文档路径 (支持 .epub / .pdf)", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(15, 2))
    file_frame = tk.Frame(root)
    file_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
    entry = tk.Entry(file_frame, textvariable=selected_path, font=("Segoe UI", 10), bd=2, relief=tk.GROOVE)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))
    
    def select_file():
        fp = filedialog.askopenfilename(title="选择文件", filetypes=[("Supported Files", "*.epub;*.pdf")])
        if fp: selected_path.set(fp)
    tk.Button(file_frame, text="浏览文件", command=select_file, bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold"), padx=10).pack(side=tk.RIGHT)
    
    tk.Label(root, text="第二栏：时延与云端流量消费监控 (Metrics)", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(10, 2))
    metrics_frame = tk.LabelFrame(root, text=" 实时云端仪表盘 ", bg="#E3F2FD", fg="#0D47A1", bd=2, relief=tk.SOLID)
    metrics_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
    lbl_metrics_data = tk.Label(metrics_frame, text="📊 [云端度量报告]\n⏱️ 实际运行: -- 分 -- 秒\n⚡ 平均耗时: -- 秒/篇\n🌐 流量消费: -- MB", font=("Consolas", 11, "bold"), bg="#E3F2FD", fg="#1565C0", justify=tk.LEFT, anchor="w", padx=15, pady=10)
    lbl_metrics_data.pack(fill=tk.X)
    
    tk.Label(root, text="第三栏：流水线执行日志 (Logs)", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(0, 2))
    log_frame = tk.Frame(root)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
    scrollbar = tk.Scrollbar(log_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text = tk.Text(log_frame, yscrollcommand=scrollbar.set, bg="#1E1E1E", fg="#A9B7C6", font=("Consolas", 10))
    log_text.pack(fill=tk.BOTH, expand=True)
    scrollbar.config(command=log_text.yview)
    
    control_frame = tk.Frame(root)
    control_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
    btn_start = tk.Button(control_frame, text="🚀 启动云端流水线", bg="#4CAF50", fg="white", font=("Segoe UI", 11, "bold"), pady=8)
    btn_stop = tk.Button(control_frame, text="🛑 紧急停止/熔断测试", command=lambda: stop_conversion(log_text, btn_stop), bg="#F44336", fg="white", font=("Segoe UI", 11, "bold"), pady=8, state=tk.DISABLED)
    
    # 🔗 这里已经修复了引发报错的括号配对逻辑
    btn_start.config(command=lambda: start_conversion(selected_path.get(), log_text, lbl_metrics_data, btn_start, btn_stop))
    btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True)
    
    log_text.insert(tk.END, "💡 熔断功能使用指南 (v2.5)：\n* 当你点击绿色按钮启动转换后，红色的【紧急停止】按钮将自动亮起。\n* 转换过程中，如果你只想冒烟测试一两页文档，可以直接点击红色按钮。系统会优雅刹车，并当场为您结算已转好文件的用时和网络流量！\n------------------------------------------------------------\n")
    root.mainloop()

if __name__ == "__main__":
    create_gui()