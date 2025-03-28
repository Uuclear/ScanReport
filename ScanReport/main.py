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
        
        # 批量处理按钮
        self.process_btn = ttk.Button(
            process_frame, 
            text="批量处理", 
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
            
            # 创建输出子文件夹
            limis_folder = os.path.join(self.export_folder, "Limis")
            association_folder = os.path.join(self.export_folder, "协会")
            other_folder = os.path.join(self.export_folder, "其他")
            
            os.makedirs(limis_folder, exist_ok=True)
            os.makedirs(association_folder, exist_ok=True)
            os.makedirs(other_folder, exist_ok=True)
            
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
                self.progress_var.set((processed / total_files) * 50)
            
            if self.stop_processing:
                raise Exception("处理已停止")
            
            # 对所有图片进行OCR并匹配重命名
            renamed_files = {}  # 用于存储重命名后的文件 {新名称: [文件路径列表, 类型]}
            total_images = len(temp_image_files)
            
            for i, img_path in enumerate(temp_image_files):
                if self.stop_processing:
                    break
                
                img_name = os.path.basename(img_path)
                self.add_log(f"OCR识别: {img_name}")
                self.status_label.config(text=f"OCR识别: {img_name}")
                
                # 提取文本并匹配
                try:
                    text, rotated = self.ocr_image(img_path)
                    
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
                    
                    # 存储文件信息，包括图像是否已旋转的标志
                    if new_name in renamed_files:
                        renamed_files[new_name][0].append(img_path)
                        renamed_files[new_name][2] = renamed_files[new_name][2] or rotated
                    else:
                        renamed_files[new_name] = [[img_path], file_type, rotated]
                    
                except Exception as e:
                    # OCR错误处理
                    self.add_log(f"处理图片时出错: {str(e)}")
                    base_name = os.path.splitext(os.path.basename(img_path))[0]
                    if base_name in renamed_files:
                        renamed_files[base_name][0].append(img_path)
                    else:
                        renamed_files[base_name] = [[img_path], "other", False]
                
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
                is_rotated = file_info[2]  # 是否有旋转的图像
                
                self.add_log(f"处理文件: {new_name} (类型: {file_type})")
                self.status_label.config(text=f"处理文件: {new_name}")
                
                # 根据文件类型选择输出目录
                if file_type == "limis":
                    output_folder = limis_folder
                elif file_type == "association":
                    output_folder = association_folder
                else:
                    output_folder = other_folder
                
                output_pdf_path = os.path.join(output_folder, f"{new_name}.pdf")
                
                # 将图片转换为PDF并合并
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
            self.add_log(f"LIMIS文件: {os.path.join(self.export_folder, 'Limis')}")
            self.add_log(f"协会文件: {os.path.join(self.export_folder, '协会')}")
            self.add_log(f"其他文件: {os.path.join(self.export_folder, '其他')}")
            
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
    
    def ocr_image(self, image_path):
        """使用PaddleOCR识别图片中的文本，返回文本和是否旋转的标志"""
        try:
            # 打开并预处理图像
            img = Image.open(image_path)
            rotated = False  # 是否进行了旋转
            
            # 尝试直接进行OCR识别
            result = self.ocr.ocr(image_path, cls=True)
            
            # 检查结果是否为空列表或第一项为空
            if not result or not result[0]:
                # 如原始识别失败，尝试旋转图像后重新识别
                self.add_log(f"原始方向识别失败，尝试旋转图像...")
                
                # 尝试不同角度的旋转
                angles = [90, 180, 270]
                for angle in angles:
                    rotated_img = img.rotate(angle, expand=True)
                    
                    # 保存临时旋转后的图像
                    temp_rotated = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    temp_rotated.close()
                    
                    # 转换为RGB并移除ICC配置文件以避免警告
                    rotated_img = rotated_img.convert('RGB')
                    rotated_img.save(temp_rotated.name, 'PNG', icc_profile=None)
                    
                    # 尝试识别旋转后的图像
                    try:
                        self.add_log(f"尝试旋转 {angle} 度进行识别...")
                        rotate_result = self.ocr.ocr(temp_rotated.name, cls=True)
                        
                        # 如果旋转后识别到文本，使用这个结果
                        if rotate_result and rotate_result[0]:
                            self.add_log(f"旋转 {angle} 度后成功识别!")
                            result = rotate_result
                            rotated = True  # 标记为已旋转
                            
                            # 将旋转后的图像替换原图
                            rotated_img.save(image_path, 'PNG', icc_profile=None)
                            break
                    except Exception as e:
                        self.add_log(f"旋转 {angle} 度识别失败: {str(e)}")
                    finally:
                        # 清理临时文件
                        try:
                            os.unlink(temp_rotated.name)
                        except:
                            pass
            
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
            
            return all_text, rotated
        except Exception as e:
            self.add_log(f"OCR识别失败: {str(e)}")
            # 直接返回空字符串而不是抛出异常，让程序继续处理
            return "", False
    
    def images_to_pdf(self, image_paths, output_pdf_path):
        """将图片转换为PDF并合并，确保正确方向"""
        try:
            pdf_writer = PyPDF2.PdfWriter()
            
            for img_path in image_paths:
                if self.stop_processing:
                    break
                
                # 使用PIL打开图片
                img = Image.open(img_path)
                img = img.convert('RGB')  # 转换为RGB以避免颜色配置文件问题
                
                # 创建临时PDF文件保存单个图片
                temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                temp_pdf.close()
                
                # 保存为PDF，不使用ICC配置文件
                img.save(temp_pdf.name, 'PDF', resolution=100.0, icc_profile=None)
                
                # 打开临时PDF并添加到PDF写入器
                with open(temp_pdf.name, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        pdf_writer.add_page(page)
                
                # 删除临时PDF
                os.unlink(temp_pdf.name)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
            
            # 写入最终PDF
            with open(output_pdf_path, 'wb') as f:
                pdf_writer.write(f)
        except Exception as e:
            self.add_log(f"图片转PDF失败: {str(e)}")
            raise

if __name__ == "__main__":
    root = tk.Tk()
    app = ScanReportApp(root)
    root.mainloop() 