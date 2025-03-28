import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import logging
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
import img2pdf
import fitz  # PyMuPDF
import re
import shutil
from datetime import datetime
import traceback
import tempfile
import time
import sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None  # 禁用图片大小限制

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 使用说明文本
HELP_TEXT = """文件批处理工具使用说明

功能介绍：
1. 支持批量处理PDF和图片文件（pdf、png、jpg、jpeg）
2. 自动OCR识别文件内容并重命名
3. 自动合并同名文件
4. 支持PDF修复和转换

使用步骤：
1. 点击"选择文件"按钮
   - 可以选择多个文件
   - 支持PDF、PNG、JPG、JPEG格式

2. 点击"导出文件夹"按钮
   - 选择处理后文件的保存位置
   - 按钮会显示选择的完整路径

3. 点击"批量处理"按钮开始处理
   - 自动处理所有选中的文件
   - 可以通过"停止"按钮中断处理

处理流程：
1. PDF文件会自动转换为图片
2. 对所有图片进行OCR识别
3. 使用正则表达式匹配文件名
   匹配模式：\\w{5}[-_—]\\d{6}
4. 将匹配到的内容作为新文件名
5. 自动合并同名文件为PDF

注意事项：
1. 确保文件未被加密或损坏
2. 大文件处理可能需要较长时间
3. 建议定期备份重要文件
4. 如果出现错误会在日志中显示
"""

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("文件批处理工具")
        self.root.geometry("1200x800")
        
        # 存储选择的文件和导出路径
        self.selected_files = []
        self.export_folder = ""
        
        # 停止标志
        self.stop_flag = False
        
        # 创建界面元素
        self.create_widgets()
        
        # 初始化OCR
        self.ocr = None
        
        # 设置PDF处理参数
        self.pdf_dpi = 200  # 降低DPI以减少内存使用
        self.max_retries = 3  # 最大重试次数
    
    def create_widgets(self):
        # 创建左右分栏
        left_frame = ttk.Frame(self.root, padding="10")
        left_frame.pack(side="left", fill="both", expand=True)
        
        right_frame = ttk.Frame(self.root, padding="10")
        right_frame.pack(side="right", fill="both")
        
        # 左侧操作区域
        # 选择文件按钮
        self.select_files_btn = ttk.Button(
            left_frame,
            text="选择文件",
            command=self.select_files,
            width=30
        )
        self.select_files_btn.pack(pady=10)
        
        # 显示选择的文件数量
        self.files_label = ttk.Label(left_frame, text="未选择文件")
        self.files_label.pack(pady=5)
        
        # 选择导出文件夹按钮（使用Label显示路径）
        folder_frame = ttk.Frame(left_frame)
        folder_frame.pack(fill="x", pady=10)
        
        self.select_folder_btn = ttk.Button(
            folder_frame,
            text="导出文件夹",
            command=self.select_export_folder,
            width=30
        )
        self.select_folder_btn.pack(pady=5)
        
        self.folder_path_label = ttk.Label(
            folder_frame,
            text="",
            wraplength=400  # 允许文本换行
        )
        self.folder_path_label.pack(pady=5)
        
        # 进度条
        self.progress = ttk.Progressbar(
            left_frame,
            orient="horizontal",
            length=300,
            mode="determinate"
        )
        self.progress.pack(pady=10)
        
        # 状态标签
        self.status_label = ttk.Label(left_frame, text="")
        self.status_label.pack(pady=5)
        
        # 批量处理按钮
        self.process_btn = ttk.Button(
            left_frame,
            text="批量处理",
            command=self.process_files,
            width=30
        )
        self.process_btn.pack(pady=10)
        
        # 停止按钮
        self.stop_btn = ttk.Button(
            left_frame,
            text="停止",
            command=self.stop_processing,
            width=30,
            state="disabled"
        )
        self.stop_btn.pack(pady=10)
        
        # 日志文本框
        log_frame = ttk.Frame(left_frame)
        log_frame.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(log_frame, height=10, width=60)
        self.log_text.pack(side="left", fill="both", expand=True)
        
        # 日志滚动条
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # 右侧帮助文档
        help_frame = ttk.LabelFrame(right_frame, text="使用说明", padding="5")
        help_frame.pack(fill="both", expand=True)
        
        self.help_text = tk.Text(help_frame, width=40, wrap="word")
        self.help_text.pack(side="left", fill="both", expand=True)
        self.help_text.insert("1.0", HELP_TEXT)
        self.help_text.configure(state="disabled")
        
        # 帮助文档滚动条
        help_scrollbar = ttk.Scrollbar(help_frame, orient="vertical", command=self.help_text.yview)
        help_scrollbar.pack(side="right", fill="y")
        self.help_text.configure(yscrollcommand=help_scrollbar.set)
    
    def update_status(self, message):
        self.status_label.config(text=message)
        self.log_text.insert(tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def select_files(self):
        filetypes = (
            ("支持的文件", "*.pdf *.png *.jpg *.jpeg"),
            ("PDF文件", "*.pdf"),
            ("PNG文件", "*.png"),
            ("JPG文件", "*.jpg *.jpeg"),
        )
        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=filetypes
        )
        if files:
            self.selected_files = list(files)
            self.files_label.config(text=f"已选择 {len(files)} 个文件")
            self.update_status(f"已选择 {len(files)} 个文件")
    
    def select_export_folder(self):
        folder = filedialog.askdirectory(title="选择导出文件夹")
        if folder:
            self.export_folder = folder
            self.folder_path_label.config(text=folder)
            self.update_status(f"已选择导出文件夹: {folder}")
    
    def stop_processing(self):
        self.stop_flag = True
        self.update_status("正在停止处理...")
        self.stop_btn.config(state="disabled")
    
    def is_valid_pdf(self, pdf_path):
        """使用PyMuPDF检查PDF文件是否有效"""
        try:
            doc = fitz.open(pdf_path)
            page_count = doc.page_count
            doc.close()
            return page_count > 0
        except Exception as e:
            logging.error(f"PDF验证失败 {pdf_path}: {str(e)}")
            return False
    
    def repair_pdf(self, pdf_path, output_path):
        """尝试修复PDF文件"""
        try:
            doc = fitz.open(pdf_path)
            doc.save(output_path, clean=True, deflate=True)
            doc.close()
            return True
        except Exception as e:
            logging.error(f"PDF修复失败 {pdf_path}: {str(e)}")
            return False
    
    def convert_pdf_page_to_image(self, pdf_path, page_number, output_path):
        """使用PyMuPDF将单个PDF页面转换为图片"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_number]
            
            # 设置更高的分辨率
            zoom = 2  # 增加清晰度
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            pix.save(output_path)
            
            doc.close()
            return True
        except Exception as e:
            logging.error(f"PDF页面转换失败 {pdf_path} 第{page_number}页: {str(e)}")
            return False
    
    def convert_pdf_to_images(self, pdf_path, temp_dir):
        """使用PyMuPDF转换PDF为图片"""
        try:
            if not self.is_valid_pdf(pdf_path):
                # 尝试修复PDF
                temp_pdf = os.path.join(temp_dir, "repaired.pdf")
                if not self.repair_pdf(pdf_path, temp_pdf):
                    raise ValueError(f"无法修复PDF文件: {pdf_path}")
                pdf_path = temp_pdf
            
            doc = fitz.open(pdf_path)
            image_paths = []
            
            for page_num in range(doc.page_count):
                if self.stop_flag:
                    doc.close()
                    return []
                
                self.update_status(f"正在转换PDF第 {page_num + 1}/{doc.page_count} 页")
                
                # 使用临时文件
                output_path = os.path.join(temp_dir, f"page_{page_num + 1}.png")
                
                if self.convert_pdf_page_to_image(pdf_path, page_num, output_path):
                    image_paths.append(output_path)
                
                # 强制清理内存
                import gc
                gc.collect()
            
            doc.close()
            return image_paths
            
        except Exception as e:
            logging.error(f"PDF转换失败 {pdf_path}: {str(e)}")
            logging.error(traceback.format_exc())
            raise
    
    def initialize_ocr(self):
        if self.ocr is None:
            self.update_status("初始化OCR引擎...")
            self.ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    
    def perform_ocr(self, image_path):
        try:
            self.update_status(f"正在OCR识别: {os.path.basename(image_path)}")
            result = self.ocr.ocr(image_path, cls=True)
            if result[0]:
                text = "\n".join([line[1][0] for line in result[0]])
                return text
            return ""
        except Exception as e:
            logging.error(f"OCR识别失败 {image_path}: {str(e)}")
            logging.error(traceback.format_exc())
            return ""
    
    def merge_pdfs(self, pdf_paths, output_path):
        """使用PyMuPDF合并PDF文件"""
        try:
            doc_output = fitz.open()
            
            for pdf_path in pdf_paths:
                if self.is_valid_pdf(pdf_path):
                    doc_input = fitz.open(pdf_path)
                    doc_output.insert_pdf(doc_input)
                    doc_input.close()
                else:
                    logging.warning(f"跳过无效的PDF文件: {pdf_path}")
            
            doc_output.save(output_path, clean=True, deflate=True)
            doc_output.close()
            
        except Exception as e:
            logging.error(f"PDF合并失败: {str(e)}")
            logging.error(traceback.format_exc())
            raise
    
    def convert_image_to_pdf(self, image_path, output_path):
        try:
            # 检查图片是否存在且可访问
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            # 尝试打开图片以验证其有效性
            with Image.open(image_path) as img:
                img.verify()
            
            # 使用PyMuPDF转换图片为PDF
            doc = fitz.open()
            img_rect = fitz.Rect(0, 0, 595, 842)  # A4大小
            page = doc.new_page(width=595, height=842)
            page.insert_image(img_rect, filename=image_path)
            doc.save(output_path, clean=True, deflate=True)
            doc.close()
            
        except Exception as e:
            logging.error(f"图片转PDF失败 {image_path}: {str(e)}")
            logging.error(traceback.format_exc())
            raise
    
    def process_files(self):
        if not self.selected_files:
            messagebox.showerror("错误", "请先选择要处理的文件")
            return
        
        if not self.export_folder:
            messagebox.showerror("错误", "请先选择导出文件夹")
            return
        
        # 重置停止标志
        self.stop_flag = False
        
        # 禁用按钮
        self.select_files_btn.config(state='disabled')
        self.select_folder_btn.config(state='disabled')
        self.process_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        # 使用临时目录
        temp_dir = tempfile.mkdtemp()
        try:
            # 初始化OCR
            self.initialize_ocr()
            
            # 存储处理后的文件信息
            processed_files = {}
            
            # 设置进度条
            total_files = len(self.selected_files)
            self.progress["maximum"] = total_files
            self.progress["value"] = 0
            
            # 处理每个文件
            for index, file_path in enumerate(self.selected_files, 1):
                if self.stop_flag:
                    self.update_status("处理已停止")
                    break
                
                try:
                    file_name = os.path.basename(file_path)
                    file_ext = os.path.splitext(file_name)[1].lower()
                    
                    self.update_status(f"处理文件 ({index}/{total_files}): {file_name}")
                    
                    # 如果是PDF，先转换为图片
                    if file_ext == '.pdf':
                        image_paths = self.convert_pdf_to_images(file_path, temp_dir)
                        if not image_paths:  # 如果转换被中断
                            continue
                    else:
                        image_paths = [file_path]
                    
                    # 对每个图片进行OCR
                    for img_path in image_paths:
                        if self.stop_flag:
                            break
                        
                        text = self.perform_ocr(img_path)
                        
                        # 使用正则表达式匹配
                        matches = re.findall(r'\w{5}[-_—]\d{6}', text)
                        if matches:
                            new_name = matches[0]
                            
                            # 如果已经存在同名文件，合并为PDF
                            if new_name in processed_files:
                                if file_ext == '.pdf':
                                    merged_path = os.path.join(self.export_folder, f"{new_name}.pdf")
                                    self.merge_pdfs([processed_files[new_name], file_path], merged_path)
                                    processed_files[new_name] = merged_path
                                else:
                                    # 如果是图片，转换为PDF后合并
                                    temp_pdf = os.path.join(temp_dir, f"{new_name}_temp.pdf")
                                    self.convert_image_to_pdf(img_path, temp_pdf)
                                    merged_path = os.path.join(self.export_folder, f"{new_name}.pdf")
                                    self.merge_pdfs([processed_files[new_name], temp_pdf], merged_path)
                                    processed_files[new_name] = merged_path
                            else:
                                # 如果是新文件
                                output_path = os.path.join(self.export_folder, f"{new_name}.pdf")
                                if file_ext == '.pdf':
                                    # 使用PyMuPDF复制PDF
                                    doc = fitz.open(file_path)
                                    doc.save(output_path, clean=True, deflate=True)
                                    doc.close()
                                else:
                                    self.convert_image_to_pdf(img_path, output_path)
                                processed_files[new_name] = output_path
                    
                    # 更新进度条
                    self.progress["value"] = index
                    self.root.update()
                    
                    # 强制垃圾回收
                    if index % 5 == 0:  # 每处理5个文件
                        import gc
                        gc.collect()
                
                except Exception as e:
                    logging.error(f"处理文件失败 {file_path}: {str(e)}")
                    logging.error(traceback.format_exc())
                    messagebox.showwarning("警告", f"处理文件 {file_name} 时出现错误: {str(e)}\n程序将继续处理其他文件")
            
            if not self.stop_flag:
                self.update_status("处理完成！")
                messagebox.showinfo("成功", "文件处理完成！")
            
        except Exception as e:
            logging.error(f"处理过程中出现错误: {str(e)}")
            logging.error(traceback.format_exc())
            messagebox.showerror("错误", f"处理过程中出现错误：{str(e)}")
        
        finally:
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logging.error(f"清理临时文件失败: {str(e)}")
            
            # 重新启用按钮
            self.select_files_btn.config(state='normal')
            self.select_folder_btn.config(state='normal')
            self.process_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            
            # 重置停止标志
            self.stop_flag = False

if __name__ == "__main__":
    # 设置更大的递归限制
    sys.setrecursionlimit(10000)
    
    root = tk.Tk()
    app = App(root)
    root.mainloop()