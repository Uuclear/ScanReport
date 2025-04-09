# 报告扫描系统

这是一个用于报告扫描、识别和管理的系统。

## 功能特点

- 报告查询和下载
- 实时扫描和OCR识别
- 二维码识别
- 批量文件导入
- 自动分类和整理

## 系统要求

- Python 3.12.9
- Node.js 18+
- MySQL 8.0+

## 安装步骤

### 后端设置

1. 创建并激活虚拟环境：
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置数据库：
- 创建MySQL数据库：`scanreport`
- 修改 `backend/backend/settings.py` 中的数据库配置

4. 运行数据库迁移：
```bash
python manage.py makemigrations
python manage.py migrate
```

5. 启动后端服务：
```bash
python manage.py runserver
```

### 前端设置

1. 安装依赖：
```bash
cd frontend
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

## 使用说明

1. 访问 http://localhost:5173 打开系统
2. 选择功能：
   - 查询：搜索和下载报告
   - 扫描：使用摄像头扫描报告
   - 导入：上传本地文件

### 扫描功能快捷键

- `+`：拍照
- `0`：保存

## 目录结构

```
.
├── backend/                # Django后端
│   ├── report/            # 报告应用
│   ├── media/             # 媒体文件
│   └── requirements.txt   # Python依赖
└── frontend/              # Vue前端
    ├── src/
    │   ├── views/        # 页面组件
    │   ├── router/       # 路由配置
    │   └── App.vue       # 主应用
    └── package.json      # Node.js依赖
```

## 注意事项

1. 确保摄像头可用
2. 确保有足够的磁盘空间存储报告
3. 定期备份数据库

## 项目介绍
这是一个用于扫描、识别和整理各类报告的Web应用程序。系统支持拍照、OCR识别、二维码扫描，能够自动提取和归类不同系统的报告。

## 功能特性
- 实时相机拍照和图像捕获
- 文档边界自动检测与透视变换
- OCR文本识别和提取
- 二维码扫描识别
- 报告信息自动提取
- 多图合并为PDF
- 报告分类归档管理
- 支持LIMS和SCETIA系统报告识别

## 技术栈
- 前端：Vue.js + Vite
- 后端：Django
- 图像处理：OpenCV + PyTesseract
- 二维码识别：pyzbar
- 数据库：MySQL

## 目录结构
```
Web-UI/
├── frontend/         # 前端Vue.js项目
├── backend/          # 后端Django项目
├── venv/             # Python虚拟环境
```

## 系统要求
- Python 3.8+
- Node.js 16+
- MySQL 5.7+

## 初始化与运行

### 后端初始化
```bash
# 切换到后端目录
cd backend

# 激活虚拟环境
venv\Scripts\activate

# 安装必要的依赖
pip install qrcode opencv-python-headless Pillow django django-cors-headers reportlab pytesseract pymupdf requests beautifulsoup4 pyzbar

# 创建数据库（需要先在MySQL中创建scanreport数据库）
python manage.py makemigrations report
python manage.py migrate

# 运行后端服务器
python manage.py runserver
```

### 前端初始化
```bash
# 切换到前端目录
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev
```

## 使用说明
1. 启动前后端服务
2. 打开浏览器访问 http://localhost:3000/
3. 使用相机拍摄文档
4. 系统会自动识别文档边界、进行文字和二维码识别
5. 可以查看、编辑识别结果
6. 保存后，系统会将文档分类并归档

## 目录说明
- media/report_pic：存储原始图片
- media/reports：按系统和项目分类存储PDF文件
- media/tmp_pic：临时图片存储
- media/trash：删除的文件暂存 