import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import pdf2image
from paddleocr import PaddleOCR
from PIL import Image
import PyPDF2
import tempfile
import shutil
import threading
from pathlib import Path
import subprocess
import sys

class ScanReportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("扫描报告处理工具")
        self.root.geometry("950x600")  # 增加宽度以容纳README显示
        
        self.selected_files = []
        self.export_folder = ""
        self.processing = False
        self.stop_processing = False
        
        # 创建主框架
        main_frame = ttk.Frame(root)
        main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # README框架
        readme_frame = ttk.LabelFrame(root, text="使用说明")
        readme_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建README显示文本框
        self.readme_text = scrolledtext.ScrolledText(readme_frame, wrap=tk.WORD, width=40, height=30)
        self.readme_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.readme_text.config(state=tk.DISABLED)
        
        # 设置README文本框的字体和样式
        self.readme_text.config(font=("Arial", 10))
        
        # 加载README文件内容
        self.load_readme()
        
        # 已选择文件标签
        self.files_label = ttk.Label(main_frame, text="已选择了0个文件")
        self.files_label.pack(fill=tk.X, pady=(0, 10))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 选择文件按钮
        self.select_files_btn = ttk.Button(
            button_frame, 
            text="选择文件", 
            command=self.select_files
        )
        self.select_files_btn.pack(side=tk.LEFT, padx=5)
        
        # 导出文件夹按钮和标签框架
        export_frame = ttk.Frame(main_frame)
        export_frame.pack(fill=tk.X, pady=10)
        
        # 导出文件夹按钮
        self.export_folder_btn = ttk.Button(
            export_frame, 
            text="导出文件夹", 
            command=self.select_export_folder
        )
        self.export_folder_btn.pack(side=tk.LEFT, padx=5)
        
        # 打开文件夹按钮
        self.open_folder_btn = ttk.Button(
            export_frame, 
            text="打开文件夹", 
            command=self.open_export_folder,
            state=tk.DISABLED
        )
        self.open_folder_btn.pack(side=tk.RIGHT, padx=5)
        
        # 导出文件夹路径标签
        self.folder_path_label = ttk.Label(export_frame, text="未选择导出文件夹")
        self.folder_path_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # 处理按钮框架
        process_frame = ttk.Frame(main_frame)
        process_frame.pack(fill=tk.X, pady=10)
        
        # 简单批量处理按钮（只识别文字方向）
        self.simple_process_btn = ttk.Button(
            process_frame, 
            text="批量处理", 
            command=self.start_simple_batch_process
        )
        self.simple_process_btn.pack(side=tk.LEFT, padx=5)
        
        # 高级批量处理按钮（带方向修正）
        self.process_btn = ttk.Button(
            process_frame, 
            text="批量处理（修正方向）", 
            command=self.start_batch_process
        )
        self.process_btn.pack(side=tk.LEFT, padx=5)
        
        # 停止按钮
        self.stop_btn = ttk.Button(
            process_frame, 
            text="停止", 
            command=self.stop_batch_process,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var, 
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=10)
        
        # 进度日志文本框
        self.log_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=10)
        self.log_text.config(state=tk.DISABLED)
        
        # 初始化OCR引擎
        self.ocr = None
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="就绪")
        self.status_label.pack(anchor=tk.W)
    
    def load_readme(self):
        """加载README文件内容并格式化为优雅的文字描述"""
        readme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
                
                # 转换Markdown格式为更友好的文本显示
                formatted_content = self.format_markdown_to_text(readme_content)
                
                self.readme_text.config(state=tk.NORMAL)
                self.readme_text.delete(1.0, tk.END)
                self.readme_text.insert(tk.END, formatted_content)
                
                # 应用文本标签样式
                self.apply_text_styles()
                
                self.readme_text.config(state=tk.DISABLED)
        except Exception as e:
            self.readme_text.config(state=tk.NORMAL)
            self.readme_text.delete(1.0, tk.END)
            self.readme_text.insert(tk.END, f"无法加载README文件: {str(e)}")
            self.readme_text.config(state=tk.DISABLED)
    
    def format_markdown_to_text(self, markdown_text):
        """将Markdown格式转换为更友好的纯文本格式"""
        lines = markdown_text.split('\n')
        formatted_lines = []
        
        for line in lines:
            # 处理标题
            if line.startswith('# '):
                formatted_lines.append("\n" + line[2:].upper() + "\n" + "=" * len(line[2:]) + "\n")
            elif line.startswith('## '):
                formatted_lines.append("\n" + line[3:] + "\n" + "-" * len(line[3:]) + "\n")
            elif line.startswith('### '):
                formatted_lines.append("\n" + line[4:] + ":\n")
            # 处理列表项
            elif line.startswith('- '):
                formatted_lines.append("• " + line[2:])
            elif line.startswith('  - '):
                formatted_lines.append("  ◦ " + line[4:])
            # 跳过代码块标记
            elif line.startswith('```'):
                continue
            # 保留其他行
            else:
                formatted_lines.append(line)
        
        # 替换代码格式
        text = '\n'.join(formatted_lines)
        
        # 处理强调
        text = re.sub(r'`([^`]+)`', r'【\1】', text)
        
        return text
    
    def apply_text_styles(self):
        """为文本添加样式标签"""
        self.readme_text.tag_configure("title", font=("Arial", 12, "bold"))
        self.readme_text.tag_configure("subtitle", font=("Arial", 11, "bold"))
        self.readme_text.tag_configure("bullet", font=("Arial", 10))
        
        # 应用标题样式
        content = self.readme_text.get(1.0, tk.END)
        lines = content.split('\n')
        
        line_number = 1
        for line in lines:
            if line and all(c == '=' for c in line):
                self.readme_text.tag_add("title", f"{line_number-1}.0", f"{line_number-1}.end")
            if line and all(c == '-' for c in line):
                self.readme_text.tag_add("subtitle", f"{line_number-1}.0", f"{line_number-1}.end")
            if line.startswith('• ') or line.startswith('  ◦ '):
                self.readme_text.tag_add("bullet", f"{line_number}.0", f"{line_number}.end")
            line_number += 1
    
    def add_log(self, message):
        """添加日志消息到日志文本框"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def select_files(self):
        """选择文件功能"""
        filetypes = (
            ("支持的文件类型", "*.pdf *.png *.jpg *.jpeg"),
            ("PDF文件", "*.pdf"),
            ("PNG文件", "*.png"),
            ("JPG文件", "*.jpg *.jpeg"),
            ("所有文件", "*.*")
        )
        files = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=filetypes
        )
        
        if files:
            self.selected_files = list(files)
            self.files_label.config(text=f"已选择了 {len(self.selected_files)} 个文件")
            self.add_log(f"已选择 {len(self.selected_files)} 个文件")
    
    def select_export_folder(self):
        """选择导出文件夹功能"""
        folder = filedialog.askdirectory(title="选择导出文件夹")
        if folder:
            self.export_folder = folder
            self.folder_path_label.config(text=folder)
            self.open_folder_btn.config(state=tk.NORMAL)
            self.add_log(f"导出文件夹: {folder}")
    
    def open_export_folder(self):
        """打开导出文件夹"""
        if not self.export_folder or not os.path.exists(self.export_folder):
            messagebox.showerror("错误", "导出文件夹不存在")
            return
        
        # 根据操作系统打开文件夹
        if os.name == 'nt':  # Windows
            os.startfile(self.export_folder)
        elif os.name == 'posix':  # macOS or Linux
            subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', self.export_folder])
    
    def start_batch_process(self):
        """在新线程中启动批量处理"""
        if not self.selected_files:
            messagebox.showerror("错误", "请先选择文件")
            return
        
        if not self.export_folder:
            messagebox.showerror("错误", "请先选择导出文件夹")
            return
        
        # 防止重复点击
        if self.processing:
            return
        
        # 更新UI状态
        self.processing = True
        self.stop_processing = False
        self.simple_process_btn.config(state=tk.DISABLED)
        self.process_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # 清空日志
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 创建线程
        thread = threading.Thread(target=self.batch_process)
        thread.daemon = True
        thread.start()
    
    def stop_batch_process(self):
        """停止批量处理"""
        if self.processing:
            self.stop_processing = True
            self.add_log("正在停止处理...")
            self.stop_btn.config(state=tk.DISABLED)
    
    def batch_process(self):
        """批量处理功能"""
        # 创建临时文件夹
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 初始化OCR引擎
            if self.ocr is None:
                self.add_log("初始化OCR引擎...")
                self.ocr = PaddleOCR(
                    use_angle_cls=True,      # 启用方向分类
                    lang="ch",               # 中文识别
                    show_log=False,          # 不显示详细日志
                    use_gpu=False,           # 默认不使用GPU
                    enable_mkldnn=True,      # 启用Intel MKL-DNN加速
                    rec_model_dir=None,      # 使用默认模型路径
                    rec_char_dict_path=None, # 使用默认字典
                    det_db_box_thresh=0.5,   # 降低检测阈值，提高检出率
                    det_db_thresh=0.3        # 降低文本区域检测阈值
                )
                self.add_log("OCR引擎初始化完成")
            
            total_files = len(self.selected_files)
            processed = 0
            temp_image_files = []  # 存储所有图片文件路径
            
            # 统计不同类型的文件计数
            limis_count = 0
            association_count = 0
            other_count = 0
            
            # 存储文件名列表用于最终输出
            limis_files = []
            association_files = []
            other_files = []
            
            # 定义输出文件夹路径（但不立即创建）
            limis_folder = os.path.join(self.export_folder, "Limis")
            association_folder = os.path.join(self.export_folder, "协会")
            other_folder = os.path.join(self.export_folder, "其他")
            
            # 处理PDF文件和图片文件
            for file_path in self.selected_files:
                if self.stop_processing:
                    break
                
                file_name = os.path.basename(file_path)
                file_ext = os.path.splitext(file_name)[1].lower()
                
                self.add_log(f"处理: {file_name}")
                self.status_label.config(text=f"处理: {file_name}")
                
                # 如果是PDF，先将每页转为图片
                if file_ext == '.pdf':
                    pdf_images = self.pdf_to_images(file_path, temp_dir)
                    temp_image_files.extend(pdf_images)
                # 如果是图片，直接添加到处理列表
                elif file_ext in ['.png', '.jpg', '.jpeg']:
                    temp_image_path = os.path.join(temp_dir, file_name)
                    shutil.copy2(file_path, temp_image_path)
                    temp_image_files.append(temp_image_path)
                
                processed += 1
                self.progress_var.set((processed / total_files) * 30)
            
            if self.stop_processing:
                raise Exception("处理已停止")
            
            # 对所有图像进行方向检测和矫正
            self.add_log("进行图像方向检测和矫正...")
            corrected_images = []
            total_images = len(temp_image_files)
            
            for i, img_path in enumerate(temp_image_files):
                if self.stop_processing:
                    break
                
                img_name = os.path.basename(img_path)
                self.add_log(f"检测图像方向: {img_name}")
                self.status_label.config(text=f"检测图像方向: {img_name}")
                
                # 矫正图像方向并返回正确方向的图像路径
                corrected_path = self.correct_image_orientation(img_path)
                corrected_images.append(corrected_path)
                
                progress = 30 + ((i + 1) / total_images) * 20
                self.progress_var.set(progress)
            
            if self.stop_processing:
                raise Exception("处理已停止")
            
            # 对所有图片进行OCR并匹配重命名
            renamed_files = {}  # 用于存储重命名后的文件 {新名称: [文件路径列表, 类型]}
            total_images = len(corrected_images)
            
            for i, img_path in enumerate(corrected_images):
                if self.stop_processing:
                    break
                
                img_name = os.path.basename(img_path)
                self.add_log(f"OCR识别: {img_name}")
                self.status_label.config(text=f"OCR识别: {img_name}")
                
                # 提取文本并匹配
                try:
                    text = self.ocr_image(img_path)
                    
                    # 检查是否获取到文本
                    if not text.strip():
                        self.add_log(f"未能从图像中提取到文本，使用原文件名")
                        base_name = os.path.splitext(os.path.basename(img_path))[0]
                        new_name = base_name
                        file_type = "other"
                        self.add_log(f"使用原文件名: {base_name}")
                    else:
                        # 匹配LIMIS格式: XX000-000000
                        limis_match = re.search(r'[a-zA-Z]{2}\d{3}[-_—]\d{6}', text)
                        
                        # 匹配协会格式: XX00-000000000
                        association_match = re.search(r'[a-zA-Z]{2}\d{2}[-_—]\d{9}', text)
                        
                        if limis_match:
                            new_name = limis_match.group(0)
                            file_type = "limis"
                            self.add_log(f"匹配到LIMIS格式: {new_name}")
                        elif association_match:
                            new_name = association_match.group(0)
                            file_type = "association"
                            self.add_log(f"匹配到协会格式: {new_name}")
                        else:
                            # 如果没有匹配到，使用原文件名
                            base_name = os.path.splitext(os.path.basename(img_path))[0]
                            new_name = base_name
                            file_type = "other"
                            self.add_log(f"未匹配到格式，使用原文件名: {base_name}")
                    
                    # 存储文件信息
                    if new_name in renamed_files:
                        renamed_files[new_name][0].append(img_path)
                    else:
                        renamed_files[new_name] = [[img_path], file_type]
                    
                except Exception as e:
                    # OCR错误处理
                    self.add_log(f"处理图片时出错: {str(e)}")
                    base_name = os.path.splitext(os.path.basename(img_path))[0]
                    if base_name in renamed_files:
                        renamed_files[base_name][0].append(img_path)
                    else:
                        renamed_files[base_name] = [[img_path], "other"]
                
                progress = 50 + ((i + 1) / total_images) * 30
                self.progress_var.set(progress)
            
            if self.stop_processing:
                raise Exception("处理已停止")
            
            # 处理重命名后的文件并转换为PDF
            processed_count = 0
            total_renamed = len(renamed_files)
            
            for new_name, file_info in renamed_files.items():
                if self.stop_processing:
                    break
                
                file_paths = file_info[0]
                file_type = file_info[1]
                
                self.add_log(f"处理文件: {new_name} (类型: {file_type})")
                self.status_label.config(text=f"处理文件: {new_name}")
                
                # 根据文件类型选择输出目录并记录文件名
                if file_type == "limis":
                    output_folder = limis_folder
                    limis_count += 1
                    if new_name not in limis_files:
                        limis_files.append(new_name)
                elif file_type == "association":
                    output_folder = association_folder
                    association_count += 1
                    if new_name not in association_files:
                        association_files.append(new_name)
                else:
                    output_folder = other_folder
                    other_count += 1
                    if new_name not in other_files:
                        other_files.append(new_name)
                
                # 确保输出目录存在
                os.makedirs(output_folder, exist_ok=True)
                
                output_pdf_path = os.path.join(output_folder, f"{new_name}.pdf")
                
                # 将图片转换为PDF并合并（确保使用已经校正方向的图像）
                self.images_to_pdf(file_paths, output_pdf_path)
                self.add_log(f"生成PDF: {output_pdf_path}")
                
                processed_count += 1
                progress = 80 + ((processed_count / total_renamed) * 20)
                self.progress_var.set(progress)
            
            if self.stop_processing:
                raise Exception("处理已停止")
            
            self.progress_var.set(100)
            self.status_label.config(text=f"处理完成! 文件已保存到: {self.export_folder}")
            self.add_log(f"处理完成! 文件已保存到: {self.export_folder}")
            
            # 显示文件夹及其中的文件列表
            if limis_count > 0:
                self.add_log(f"LIMIS文件: {limis_folder} ({limis_count}个文件)")
                self.add_log("Limis报告：")
                for file_name in sorted(limis_files):
                    self.add_log(file_name)
            
            if association_count > 0:
                self.add_log(f"协会文件: {association_folder} ({association_count}个文件)")
                self.add_log("协会报告：")
                for file_name in sorted(association_files):
                    self.add_log(file_name)
            
            if other_count > 0:
                self.add_log(f"其他文件: {other_folder} ({other_count}个文件)")
                self.add_log("其他：")
                for file_name in sorted(other_files):
                    self.add_log(file_name)
            
            messagebox.showinfo("成功", f"成功处理 {len(self.selected_files)} 个文件，并输出到 {self.export_folder}")
            
        except Exception as e:
            error_msg = str(e)
            self.add_log(f"错误: {error_msg}")
            self.status_label.config(text=f"处理过程中发生错误")
            
            if error_msg != "处理已停止":
                messagebox.showerror("错误", f"处理过程中发生错误: {error_msg}")
        finally:
            # 清理临时文件夹
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            
            # 恢复UI状态
            self.processing = False
            self.simple_process_btn.config(state=tk.NORMAL)
            self.process_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            if self.stop_processing:
                self.progress_var.set(0)
                self.status_label.config(text="处理已停止")
                self.add_log("处理已停止")
            elif self.progress_var.get() == 100:
                self.status_label.config(text="处理完成")
    
    def pdf_to_images(self, pdf_path, output_dir):
        """将PDF文件转换为图片"""
        try:
            images = pdf2image.convert_from_path(pdf_path)
            image_paths = []
            
            for i, img in enumerate(images):
                # 生成输出图片路径
                base_name = os.path.basename(pdf_path)
                base_name = os.path.splitext(base_name)[0]
                img_path = os.path.join(output_dir, f"{base_name}_page_{i+1}.png")
                
                # 保存图片（移除ICC配置文件以避免libpng警告）
                img = img.convert('RGB')  # 确保图像是RGB模式
                img.save(img_path, 'PNG', icc_profile=None)  # 不包含ICC配置文件
                image_paths.append(img_path)
                
                if self.stop_processing:
                    break
            
            self.add_log(f"PDF转换为 {len(image_paths)} 张图片: {os.path.basename(pdf_path)}")
            return image_paths
        except Exception as e:
            self.add_log(f"PDF转图片出错: {str(e)}")
            raise
    
    def correct_image_orientation(self, image_path):
        """在OCR前检测并校正图像方向"""
        try:
            # 打开图像
            img = Image.open(image_path)
            
            # 获取原始图像尺寸
            orig_width, orig_height = img.size
            is_landscape = orig_width > orig_height
            
            # 尝试不同角度的旋转并检测文本
            best_angle = 0
            best_score = 0
            best_image = None
            
            # 如果是横向图像，优先尝试旋转到纵向
            angles_to_try = [0, 90, 180, 270] if is_landscape else [0, 180, 90, 270]
            
            self.add_log(f"检测图像尺寸: {orig_width}x{orig_height}, {'横向' if is_landscape else '纵向'}")
            
            # 尝试不同角度旋转
            for angle in angles_to_try:
                if angle == 0:
                    rotated_img = img.copy()
                else:
                    rotated_img = img.rotate(angle, expand=True)
                
                # 保存临时旋转图像
                temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                temp_img.close()
                
                # 转换为RGB并移除ICC配置文件
                rotated_img = rotated_img.convert('RGB')
                rotated_img.save(temp_img.name, 'PNG', icc_profile=None)
                
                # 检测这个方向的文本
                try:
                    detect_result = self.ocr.ocr(temp_img.name, cls=False)
                    
                    # 计算这个方向检测到的文本量和置信度
                    score = 0
                    confidence_sum = 0
                    
                    if detect_result and detect_result[0]:
                        score = len(detect_result[0])
                        
                        # 计算置信度总和
                        for line in detect_result[0]:
                            confidence_sum += line[1][1]  # 置信度值
                        
                        # 调整分数：文本区域数量 * 平均置信度
                        if score > 0:
                            avg_confidence = confidence_sum / score
                            adjusted_score = score * avg_confidence
                        else:
                            adjusted_score = 0
                            
                        # 如果是纵向(portrait)，给予额外的分数提升
                        rotated_width, rotated_height = rotated_img.size
                        if rotated_height > rotated_width:
                            adjusted_score *= 1.2  # 优先选择纵向图像
                            
                        self.add_log(f"旋转 {angle} 度: 检测到 {score} 个文本区域, 置信度: {avg_confidence:.2f}, 调整分数: {adjusted_score:.2f}")
                        
                        # 如果这个方向检测到更多文本或更高的调整分数，保存为最佳角度
                        if adjusted_score > best_score:
                            best_score = adjusted_score
                            best_angle = angle
                            best_image = rotated_img.copy()
                    else:
                        self.add_log(f"旋转 {angle} 度: 未检测到文本")
                    
                except Exception as e:
                    self.add_log(f"旋转 {angle} 度检测失败: {str(e)}")
                finally:
                    # 删除临时文件
                    try:
                        os.unlink(temp_img.name)
                    except:
                        pass
            
            # 用最佳角度旋转图像并保存
            if best_angle != 0 and best_image is not None:
                self.add_log(f"确定最佳旋转角度: {best_angle} 度")
                best_image.save(image_path, 'PNG', icc_profile=None)
                return image_path
            else:
                self.add_log("保持原始方向")
                # 确保原始图像也是RGB格式，以便后续处理
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    img.save(image_path, 'PNG', icc_profile=None)
                return image_path
                
        except Exception as e:
            self.add_log(f"方向校正错误: {str(e)}")
            # 尝试转换为RGB格式以确保后续处理正常
            try:
                img = Image.open(image_path).convert('RGB')
                img.save(image_path, 'PNG', icc_profile=None)
            except:
                pass
            return image_path  # 出错时返回原始路径
    
    def ocr_image(self, image_path):
        """使用PaddleOCR识别已经校正方向的图片中的文本"""
        try:
            # 直接进行OCR识别
            result = self.ocr.ocr(image_path, cls=True)
            
            # 提取所有识别到的文本
            all_text = ""
            
            # 检查结果是否有效
            if result and result[0]:
                for line in result[0]:
                    text = line[1][0]  # 提取识别文本
                    all_text += text + " "
                
                if not all_text.strip():
                    self.add_log("识别到了图像，但未提取到文本")
            else:
                self.add_log("未能检测到任何文本内容")
            
            return all_text
        except Exception as e:
            self.add_log(f"OCR识别失败: {str(e)}")
            # 直接返回空字符串而不是抛出异常，让程序继续处理
            return ""
    
    def images_to_pdf(self, image_paths, output_pdf_path):
        """将图片转换为PDF并合并，确保正确方向"""
        try:
            if not image_paths:
                self.add_log(f"警告: 没有图像可以转换为PDF: {output_pdf_path}")
                return
                
            # 使用PIL直接创建PDF而不是经过临时PDF和PyPDF2
            images = []
            
            # 首先检查所有图像是否可读取，并且转换为RGB格式
            for img_path in image_paths:
                if self.stop_processing:
                    break
                
                try:
                    # 使用PIL打开图片
                    img = Image.open(img_path)
                    
                    # 确保图像是RGB模式
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 添加到图像列表
                    images.append(img)
                except Exception as e:
                    self.add_log(f"打开图像失败: {img_path}, 错误: {str(e)}")
            
            if not images:
                self.add_log(f"警告: 无法读取任何图像来创建PDF: {output_pdf_path}")
                return
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
            
            # 保存第一张图像为PDF，并附加其余图像
            first_image = images[0]
            if len(images) == 1:
                # 只有一张图像，直接保存
                first_image.save(output_pdf_path, 'PDF', resolution=100.0, save_all=False)
            else:
                # 多张图像，使用save_all和append_images保存
                first_image.save(
                    output_pdf_path, 
                    'PDF', 
                    resolution=100.0, 
                    save_all=True, 
                    append_images=images[1:]
                )
            
            self.add_log(f"成功创建PDF: {output_pdf_path} (包含 {len(images)} 页)")
            
        except Exception as e:
            self.add_log(f"图片转PDF失败: {str(e)}")
            raise
    
    def start_simple_batch_process(self):
        """在新线程中启动简单批量处理（只识别文字方向）"""
        if not self.selected_files:
            messagebox.showerror("错误", "请先选择文件")
            return
        
        if not self.export_folder:
            messagebox.showerror("错误", "请先选择导出文件夹")
            return
        
        # 防止重复点击
        if self.processing:
            return
        
        # 更新UI状态
        self.processing = True
        self.stop_processing = False
        self.simple_process_btn.config(state=tk.DISABLED)
        self.process_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # 清空日志
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 创建线程
        thread = threading.Thread(target=self.simple_batch_process)
        thread.daemon = True
        thread.start()
    
    def simple_batch_process(self):
        """简单批量处理功能（只识别文字方向）"""
        # 创建临时文件夹
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 初始化OCR引擎
            if self.ocr is None:
                self.add_log("初始化OCR引擎...")
                self.ocr = PaddleOCR(
                    use_angle_cls=True,      # 启用方向分类
                    lang="ch",               # 中文识别
                    show_log=False,          # 不显示详细日志
                    use_gpu=False,           # 默认不使用GPU
                    enable_mkldnn=True,      # 启用Intel MKL-DNN加速
                    rec_model_dir=None,      # 使用默认模型路径
                    rec_char_dict_path=None, # 使用默认字典
                    det_db_box_thresh=0.5,   # 降低检测阈值，提高检出率
                    det_db_thresh=0.3        # 降低文本区域检测阈值
                )
                self.add_log("OCR引擎初始化完成")
            
            total_files = len(self.selected_files)
            processed = 0
            temp_image_files = []  # 存储所有图片文件路径
            
            # 统计不同类型的文件计数
            limis_count = 0
            association_count = 0
            other_count = 0
            
            # 存储文件名列表用于最终输出
            limis_files = []
            association_files = []
            other_files = []
            
            # 定义输出文件夹路径（但不立即创建）
            limis_folder = os.path.join(self.export_folder, "Limis")
            association_folder = os.path.join(self.export_folder, "协会")
            other_folder = os.path.join(self.export_folder, "其他")
            
            # 处理PDF文件和图片文件
            for file_path in self.selected_files:
                if self.stop_processing:
                    break
                
                file_name = os.path.basename(file_path)
                file_ext = os.path.splitext(file_name)[1].lower()
                
                self.add_log(f"处理: {file_name}")
                self.status_label.config(text=f"处理: {file_name}")
                
                # 如果是PDF，先将每页转为图片
                if file_ext == '.pdf':
                    pdf_images = self.pdf_to_images(file_path, temp_dir)
                    temp_image_files.extend(pdf_images)
                # 如果是图片，直接添加到处理列表
                elif file_ext in ['.png', '.jpg', '.jpeg']:
                    temp_image_path = os.path.join(temp_dir, file_name)
                    shutil.copy2(file_path, temp_image_path)
                    temp_image_files.append(temp_image_path)
                
                processed += 1
                self.progress_var.set((processed / total_files) * 30)
            
            if self.stop_processing:
                raise Exception("处理已停止")
            
            # 简单方式：只识别文字方向并旋转
            self.add_log("进行简单图像方向校正...")
            corrected_images = []
            total_images = len(temp_image_files)
            
            for i, img_path in enumerate(temp_image_files):
                if self.stop_processing:
                    break
                
                img_name = os.path.basename(img_path)
                self.add_log(f"简单方向校正: {img_name}")
                self.status_label.config(text=f"简单方向校正: {img_name}")
                
                # 使用简单方向校正
                corrected_path = self.simple_correct_orientation(img_path)
                corrected_images.append(corrected_path)
                
                progress = 30 + ((i + 1) / total_images) * 20
                self.progress_var.set(progress)
            
            if self.stop_processing:
                raise Exception("处理已停止")
            
            # 对所有图片进行OCR并匹配重命名
            renamed_files = {}  # 用于存储重命名后的文件 {新名称: [文件路径列表, 类型]}
            total_images = len(corrected_images)
            
            for i, img_path in enumerate(corrected_images):
                if self.stop_processing:
                    break
                
                img_name = os.path.basename(img_path)
                self.add_log(f"OCR识别: {img_name}")
                self.status_label.config(text=f"OCR识别: {img_name}")
                
                # 提取文本并匹配
                try:
                    text = self.ocr_image(img_path)
                    
                    # 检查是否获取到文本
                    if not text.strip():
                        self.add_log(f"未能从图像中提取到文本，使用原文件名")
                        base_name = os.path.splitext(os.path.basename(img_path))[0]
                        new_name = base_name
                        file_type = "other"
                        self.add_log(f"使用原文件名: {base_name}")
                    else:
                        # 匹配LIMIS格式: XX000-000000
                        limis_match = re.search(r'[a-zA-Z]{2}\d{3}[-_—]\d{6}', text)
                        
                        # 匹配协会格式: XX00-000000000
                        association_match = re.search(r'[a-zA-Z]{2}\d{2}[-_—]\d{9}', text)
                        
                        if limis_match:
                            new_name = limis_match.group(0)
                            file_type = "limis"
                            self.add_log(f"匹配到LIMIS格式: {new_name}")
                        elif association_match:
                            new_name = association_match.group(0)
                            file_type = "association"
                            self.add_log(f"匹配到协会格式: {new_name}")
                        else:
                            # 如果没有匹配到，使用原文件名
                            base_name = os.path.splitext(os.path.basename(img_path))[0]
                            new_name = base_name
                            file_type = "other"
                            self.add_log(f"未匹配到格式，使用原文件名: {base_name}")
                    
                    # 存储文件信息
                    if new_name in renamed_files:
                        renamed_files[new_name][0].append(img_path)
                    else:
                        renamed_files[new_name] = [[img_path], file_type]
                    
                except Exception as e:
                    # OCR错误处理
                    self.add_log(f"处理图片时出错: {str(e)}")
                    base_name = os.path.splitext(os.path.basename(img_path))[0]
                    if base_name in renamed_files:
                        renamed_files[base_name][0].append(img_path)
                    else:
                        renamed_files[base_name] = [[img_path], "other"]
                
                progress = 50 + ((i + 1) / total_images) * 30
                self.progress_var.set(progress)
            
            if self.stop_processing:
                raise Exception("处理已停止")
            
            # 处理重命名后的文件并转换为PDF
            processed_count = 0
            total_renamed = len(renamed_files)
            
            for new_name, file_info in renamed_files.items():
                if self.stop_processing:
                    break
                
                file_paths = file_info[0]
                file_type = file_info[1]
                
                self.add_log(f"处理文件: {new_name} (类型: {file_type})")
                self.status_label.config(text=f"处理文件: {new_name}")
                
                # 根据文件类型选择输出目录并记录文件名
                if file_type == "limis":
                    output_folder = limis_folder
                    limis_count += 1
                    if new_name not in limis_files:
                        limis_files.append(new_name)
                elif file_type == "association":
                    output_folder = association_folder
                    association_count += 1
                    if new_name not in association_files:
                        association_files.append(new_name)
                else:
                    output_folder = other_folder
                    other_count += 1
                    if new_name not in other_files:
                        other_files.append(new_name)
                
                # 确保输出目录存在
                os.makedirs(output_folder, exist_ok=True)
                
                output_pdf_path = os.path.join(output_folder, f"{new_name}.pdf")
                
                # 将图片转换为PDF并合并（确保使用已经校正方向的图像）
                self.images_to_pdf(file_paths, output_pdf_path)
                self.add_log(f"生成PDF: {output_pdf_path}")
                
                processed_count += 1
                progress = 80 + ((processed_count / total_renamed) * 20)
                self.progress_var.set(progress)
            
            if self.stop_processing:
                raise Exception("处理已停止")
            
            self.progress_var.set(100)
            self.status_label.config(text=f"处理完成! 文件已保存到: {self.export_folder}")
            self.add_log(f"处理完成! 文件已保存到: {self.export_folder}")
            
            # 显示文件夹及其中的文件列表
            if limis_count > 0:
                self.add_log(f"LIMIS文件: {limis_folder} ({limis_count}个文件)")
                self.add_log("Limis报告：")
                for file_name in sorted(limis_files):
                    self.add_log(file_name)
            
            if association_count > 0:
                self.add_log(f"协会文件: {association_folder} ({association_count}个文件)")
                self.add_log("协会报告：")
                for file_name in sorted(association_files):
                    self.add_log(file_name)
            
            if other_count > 0:
                self.add_log(f"其他文件: {other_folder} ({other_count}个文件)")
                self.add_log("其他：")
                for file_name in sorted(other_files):
                    self.add_log(file_name)
            
            messagebox.showinfo("成功", f"成功处理 {len(self.selected_files)} 个文件，并输出到 {self.export_folder}")
            
        except Exception as e:
            error_msg = str(e)
            self.add_log(f"错误: {error_msg}")
            self.status_label.config(text=f"处理过程中发生错误")
            
            if error_msg != "处理已停止":
                messagebox.showerror("错误", f"处理过程中发生错误: {error_msg}")
        finally:
            # 清理临时文件夹
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            
            # 恢复UI状态
            self.processing = False
            self.simple_process_btn.config(state=tk.NORMAL)
            self.process_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            if self.stop_processing:
                self.progress_var.set(0)
                self.status_label.config(text="处理已停止")
                self.add_log("处理已停止")
            elif self.progress_var.get() == 100:
                self.status_label.config(text="处理完成")
    
    def simple_correct_orientation(self, image_path):
        """简单图像方向校正，仅使用OCR的方向分类器"""
        try:
            # 打开图像
            img = Image.open(image_path)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 保存为临时文件（确保是RGB格式）
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_img.close()
            img.save(temp_img.name, 'PNG', icc_profile=None)
            
            try:
                # 使用OCR库的角度分类器对图像进行直接方向识别和校正
                self.add_log("使用OCR内置方向分类器...")
                
                # 设置use_angle_cls=True让OCR自动检测方向
                result = self.ocr.ocr(temp_img.name, cls=True)
                
                # 如果返回结果中包含了修正方向的图像，获取修正后的结果
                if hasattr(result, 'get_rotated_img'):
                    self.add_log("OCR检测到需要旋转图像")
                    rotated_img = result.get_rotated_img()
                    rotated_img.save(image_path, 'PNG', icc_profile=None)
                    self.add_log("已自动旋转图像")
                else:
                    # OCR的方向分类器不需要旋转，保持原图
                    self.add_log("OCR判断不需要旋转")
                    img.save(image_path, 'PNG', icc_profile=None)
            except Exception as e:
                self.add_log(f"方向分类错误: {str(e)}，保持原图")
                # 发生错误，保持原图
                img.save(image_path, 'PNG', icc_profile=None)
            finally:
                # 删除临时文件
                try:
                    os.unlink(temp_img.name)
                except:
                    pass
            
            return image_path
        except Exception as e:
            self.add_log(f"方向校正错误: {str(e)}")
            # 尝试确保图像是RGB格式
            try:
                img = Image.open(image_path).convert('RGB')
                img.save(image_path, 'PNG', icc_profile=None)
            except:
                pass
            return image_path

if __name__ == "__main__":
    root = tk.Tk()
    app = ScanReportApp(root)
    root.mainloop() 