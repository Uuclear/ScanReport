#!/usr/bin/env python
"""
构建脚本 - 使用Nuitka将ScanReport应用程序打包为可执行文件
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def check_requirements():
    """检查是否安装了所需的依赖"""
    try:
        import nuitka
        print(f"已找到Nuitka (版本: {nuitka.__version__})")
    except ImportError:
        print("未安装Nuitka，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka", "--upgrade"])
        print("Nuitka安装完成")

def build_executable():
    """使用Nuitka构建可执行文件"""
    print("开始构建可执行文件...")
    
    # 获取当前目录
    current_dir = Path(__file__).parent.absolute()
    
    # 主程序路径
    main_script = os.path.join(current_dir, "main.py")
    
    # 创建输出目录
    dist_dir = os.path.join(current_dir, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    
    # 设置构建命令
    build_cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",                   # 创建独立的可执行文件
        "--onefile",                      # 生成单一可执行文件
        "--include-package=tkinter",      # 包含tkinter
        "--include-package=paddleocr",    # 包含paddleocr
        "--include-package=pdf2image",    # 包含pdf2image
        "--include-package=PyPDF2",       # 包含PyPDF2
        "--include-package=PIL",          # 包含PIL (Pillow)
        "--include-data-dir=" + os.path.join(current_dir, "README.md") + "=.",  # 包含README文件
        "--windows-disable-console",      # 禁用控制台窗口
        "--windows-icon-from-ico=" + os.path.join(current_dir, "icon.ico") + "=",  # 设置图标（如果有）
        "--output-dir=" + dist_dir,       # 输出目录
        "--company-name=ScanReportApp",   # 公司名称
        "--product-name=扫描报告处理工具",  # 产品名称
        "--file-version=1.0.0",           # 文件版本
        "--product-version=1.0.0",        # 产品版本
        "--file-description=扫描报告处理工具",  # 文件描述
        "--copyright=Copyright 2023",     # 版权信息
        main_script                       # 主脚本路径
    ]
    
    # 检查是否存在图标文件，如果不存在则移除相关参数
    if not os.path.exists(os.path.join(current_dir, "icon.ico")):
        for i, arg in enumerate(build_cmd):
            if arg.startswith("--windows-icon-from-ico="):
                build_cmd.pop(i)
                break
    
    # 执行构建命令
    print("执行Nuitka编译...")
    print(f"命令: {' '.join(build_cmd)}")
    
    try:
        subprocess.check_call(build_cmd)
        print("编译完成!")
        
        # 确定构建产物的路径
        if platform.system() == "Windows":
            executable_name = "ScanReport.exe"
        else:
            executable_name = "ScanReport"
        
        built_exe = os.path.join(dist_dir, "main.dist", executable_name)
        final_exe = os.path.join(dist_dir, "扫描报告处理工具.exe" if platform.system() == "Windows" else "扫描报告处理工具")
        
        # 重命名可执行文件
        if os.path.exists(built_exe):
            if os.path.exists(final_exe):
                os.remove(final_exe)
            shutil.move(built_exe, final_exe)
            print(f"已重命名为: {final_exe}")
        
        print("构建成功!")
        print(f"可执行文件位于: {final_exe}")
        
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        return False
    
    return True

def main():
    """主入口函数"""
    print("=" * 50)
    print("扫描报告处理工具 - 打包脚本")
    print("=" * 50)
    
    # 检查依赖
    check_requirements()
    
    # 构建可执行文件
    success = build_executable()
    
    if success:
        print("\n✅ 打包完成！")
    else:
        print("\n❌ 打包失败！")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 