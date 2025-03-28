import os
import sys
import subprocess

def build_executable():
    # 获取python解释器路径
    python_path = sys.executable
    
    # Nuitka编译命令
    command = [
        python_path,
        "-m",
        "nuitka",
        "--standalone",  # 创建独立可执行文件
        "--windows-disable-console",  # 禁用控制台窗口
        "--enable-plugin=tk-inter",  # 启用tkinter插件
        "--include-package=paddleocr",  # 包含paddleocr包
        "--include-package=pdf2image",  # 包含pdf2image包
        "--include-package=PIL",  # 包含PIL包
        "--include-package=fitz",  # 包含PyMuPDF包
        "--include-package=img2pdf",  # 包含img2pdf包
        "--windows-icon-from-ico=icon.ico",  # 设置图标（如果有的话）
        "--output-dir=dist",  # 输出目录
        "main.py"  # 主程序文件
    ]
    
    # 执行编译命令
    subprocess.run(command)

if __name__ == "__main__":
    build_executable()