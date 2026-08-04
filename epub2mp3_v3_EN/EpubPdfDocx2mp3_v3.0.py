import os, re, zipfile, asyncio, time
from bs4 import BeautifulSoup
import edge_tts
from pypdf import PdfReader
from docx import Document  # 用于解析 Word 文档
import tkinter as tk
from tkinter import filedialog, messagebox

VOICE_ACTOR = "en-GB-SoniaNeural"
is_stop_requested = False

def sanitize_filename(filename):
    return re.sub(r'[\/*?:"<>|]', "", filename).strip().replace(" ", "_").replace("\n", "")[:40]

def violence_scan_epub(epub_path, log_widget):
    log_widget.insert(tk.END, "🔓 STARTING [EPUB] PAGES SCAN...\n")
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
                title_text = title_tag.get_text().strip() if title_tag else (article_text.split('\n')[:30] + "...")
                if "contents" in title_text.lower() or "index" in title_text.lower(): continue
                chapters.append({
                    "filename": f"{track_num:02d}_{sanitize_filename(title_text)}.mp3",
                    "text": f"Article {track_num}. {title_text}.\n\n{article_text}", "title": title_text
                })
                track_num += 1
    return chapters

def scan_and_extract_pdf(pdf_path, log_widget):
    log_widget.insert(tk.END, "📄 STARTING [PDF] PAGES ANALYSIS...\n")
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
            "title": f"THE {index+1} PAGE: {raw_title}"
        })
    return chapters

def scan_and_extract_docx(docx_path, log_widget):
    log_widget.insert(tk.END, "📝 STARTING [Word] PARAGRAPH ANALYSIS...\n")
    log_widget.update()
    chapters = []
    try:
        doc = Document(docx_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if paragraphs:
            raw_title = paragraphs[0] if len(paragraphs[0]) < 40 else paragraphs[0][:35] + "..."
            full_text = "\n\n".join(paragraphs)
            chapters.append({
                "filename": f"01_{sanitize_filename(raw_title)}.mp3",
                # "text": f"Word Document. Title: {raw_title}.\n\n{full_text}",  会读出Word Document. Title:
		"text": full_text,
                "title": f"Word File: {raw_title}" 
		
            })
    except Exception as e:
        log_widget.insert(tk.END, f"❌ READING Word FILE ERROR: {e}\n")
    return chapters

async def convert_single_track(text, voice, output_path):
    await edge_tts.Communicate(text, voice).save(output_path)
async def process_all_chapters(chapters, final_output_dir, log_widget, metrics_label):
    global is_stop_requested
    if not os.path.exists(final_output_dir): os.makedirs(final_output_dir)
    log_widget.insert(tk.END, f"\n🚀 ANALYSING DONE！FOUND {len(chapters)} EFFECTIVE TRACKS。START DOWNLOADING AUDIO...\n")
    
    start_time, total_bytes, success_count = time.time(), 0, 0
    for index, chapter in enumerate(chapters):
        if is_stop_requested:
            log_widget.insert(tk.END, "\n🛑 [STOP] STOP COMMAND RECEIVED，CLEANING DATA...\n")
            break
        file_path = os.path.join(final_output_dir, chapter["filename"])
        log_widget.insert(tk.END, f"🎙️ [{index+1}/{len(chapters)}] CONVERTING: {chapter['title'][:25]}...\n")
        log_widget.see(tk.END); log_widget.update()
        try:
            await convert_single_track(chapter["text"], VOICE_ACTOR, file_path)
            if os.path.exists(file_path):
                total_bytes += os.path.getsize(file_path)
                success_count += 1
        except Exception as e:
            log_widget.insert(tk.END, f"❌ DAILED: {chapter['title'][:10]}... REASON: {e}\n")
            
    total_seconds = time.time() - start_time
    minutes, seconds = int(total_seconds // 60), int(total_seconds % 60)
    avg_seconds = total_seconds / success_count if success_count else 0
    total_mb = total_bytes / (1024 * 1024)
    
    log_widget.insert(tk.END, f"\n✨ PROCESSING DONE。SUCCESFULLY CONVERTED {success_count} AUDIO。\n")
    log_widget.see(tk.END)
    metrics_label.config(text=f"📊 [CLOUD REPORT]\n⏱️ RUN TIME: {minutes} MIN {seconds} SEND\n⚡ EVERAGE TIME USED: {avg_seconds:.2f} SECOND/ARTICLE\n🌐 DATA USAGE: {total_mb:.2f} MB")
    messagebox.showwarning("NOTE", f"MISSION COMPLETE！PROCESSED {success_count} AUDIO。") if is_stop_requested else messagebox.showinfo("DONE", "ALL TRACK CONVERTED！")

def stop_conversion(log_widget, stop_btn):
    global is_stop_requested
    is_stop_requested = True
    log_widget.insert(tk.END, "\n⏳ SENRING PAUSE SIGNAL TO CLOUD, FULL STOP AFTER DURRENT CONVERT...\n")
    log_widget.see(tk.END); stop_btn.config(state=tk.DISABLED)

def start_conversion(file_path, custom_out_path, log_widget, metrics_label, start_btn, stop_btn):
    global is_stop_requested
    if not file_path:
        messagebox.showwarning("WARNING", "PLEASE SELECT A FILE BEFORE STARTING！")
        return
    is_stop_requested = False
    start_btn.config(state=tk.DISABLED); stop_btn.config(state=tk.NORMAL)
    
    if custom_out_path:
        final_output_dir = custom_out_path
    else:
        base_dir = os.path.dirname(file_path)
        file_name_only = os.path.splitext(os.path.basename(file_path))[0]
        final_output_dir = os.path.join(base_dir, f"[AUDIO]_{sanitize_filename(file_name_only)}")
        
    try:
        if file_path.lower().endswith('.epub'): all_articles = violence_scan_epub(file_path, log_widget)
        elif file_path.lower().endswith('.pdf'): all_articles = scan_and_extract_pdf(file_path, log_widget)
        elif file_path.lower().endswith('.docx'): all_articles = scan_and_extract_docx(file_path, log_widget)
        else: return
        if not all_articles: return
        asyncio.run(process_all_chapters(all_articles, final_output_dir, log_widget, metrics_label))
    except Exception as e: log_widget.insert(tk.END, f"\n❌ ERROR: {e}\n")
    finally: start_btn.config(state=tk.NORMAL); stop_btn.config(state=tk.DISABLED)

def create_gui():
    root = tk.Tk()
    root.title("CONTROL PANAL v3.0 ")
    
    # 1. 设定你想让窗口拥有的尺寸（保持你想要的 650x960 完美露出按钮）
    window_width = 650
    window_height = 960
    
    # 2. 动态获取你当前电脑屏幕的真实分辨率大小
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # 3. 计算出让窗口完美居中的初始左上角坐标点
    center_x = int((screen_width - window_width) / 2)
    center_y = int((screen_height - window_height) / 2)
    
    # 4. 动态拼接并应用坐标（相当于 root.geometry("650x960+居中X+居中Y")）
    root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
    selected_path = tk.StringVar()
    custom_output_path = tk.StringVar()
    
    tk.Label(root, text="INPUT/SELECT FILE (SUPPORT .epub / .pdf / .docx)", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(15, 2))
    file_frame = tk.Frame(root)
    file_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
    tk.Entry(file_frame, textvariable=selected_path, font=("Segoe UI", 10), bd=2, relief=tk.GROOVE).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))
    
    def select_file():
        fp = filedialog.askopenfilename(title="SELECT ARTICLE", filetypes=[("Supported Files", "*.epub;*.pdf;*.docx")])
        if fp: selected_path.set(fp)
        
    tk.Button(file_frame, text="VIEW FILES", command=select_file, bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold"), padx=10).pack(side=tk.RIGHT)
    
    tk.Label(root, text="SELECT OUT PUT PATH (IF NOT SELECTED: SAVED IN DEFAULT FOLDER)", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(5, 2))
    out_frame = tk.Frame(root)
    out_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
    tk.Entry(out_frame, textvariable=custom_output_path, font=("Segoe UI", 10), bd=2, relief=tk.GROOVE).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 10))
    
    def select_output_dir():
        dp = filedialog.askdirectory(title="SELECT A FOLDER TO SAVE AUDIO FILE")
        if dp: custom_output_path.set(dp)
        
    tk.Button(out_frame, text="FILE PATH", command=select_output_dir, bg="#9C27B0", fg="white", font=("Segoe UI", 9, "bold"), padx=10).pack(side=tk.RIGHT)
    
    tk.Label(root, text="DELAY AND CLOUD DATA USAGE MONITOR (Metrics)", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(5, 2))
    metrics_frame = tk.LabelFrame(root, text=" REALTIME PANAL ", bg="#E3F2FD", fg="#0D47A1", bd=2, relief=tk.SOLID)
    metrics_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
    lbl_metrics_data = tk.Label(metrics_frame, text="📊 [CLOUD REPORT]\n⏱️ RUN TIME: -- MIN -- SEC\n⚡ AVERAGE TIME: -- SEC/ARTICLE\n🌐 DATA USAGE: -- MB", font=("Consolas", 11, "bold"), bg="#E3F2FD", fg="#1565C0", justify=tk.LEFT, anchor="w", padx=15, pady=10)
    lbl_metrics_data.pack(fill=tk.X)
    
    tk.Label(root, text="PROCESSING LOGS (Logs)", font=("Segoe UI", 10, "bold"), anchor="w").pack(fill=tk.X, padx=15, pady=(0, 2))
    log_frame = tk.Frame(root)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
    scrollbar = tk.Scrollbar(log_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text = tk.Text(log_frame, yscrollcommand=scrollbar.set, bg="#1E1E1E", fg="#A9B7C6", font=("Consolas", 10))
    log_text.pack(fill=tk.BOTH, expand=True)
    scrollbar.config(command=log_text.yview)
    
    control_frame = tk.Frame(root)
    control_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
    btn_start = tk.Button(control_frame, text="🚀 START CLOUD PROCESSING LINE", bg="#4CAF50", fg="white", font=("Segoe UI", 11, "bold"), pady=8)
    btn_stop = tk.Button(control_frame, text="🛑 STOP/HAULT TEST", command=lambda: stop_conversion(log_text, btn_stop), bg="#F44336", fg="white", font=("Segoe UI", 11, "bold"), pady=8, state=tk.DISABLED)
    btn_start.config(command=lambda: start_conversion(selected_path.get(), custom_output_path.get(), log_text, lbl_metrics_data, btn_start, btn_stop))
    btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True)
    
    log_text.insert(tk.END, "💡 USER GUIDE (v3.0)：\n* IF【FILE PATH】IS EMPTY，A NEW FOLDER WILL BE CREATED\n------------------------------------------------------------\n")
    root.mainloop()

if __name__ == "__main__":
    create_gui()

