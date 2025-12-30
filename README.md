# reader 3

![my_reader](my_reader.png)

一个轻量级的、自托管的 EPUB/PDF 阅读器，支持按章节阅读 EPUB 和 PDF 书籍。
来自 karpathy 的项目[reader](https://github.com/karpathy/reader3/)，修改了一些功能。

## 项目架构

- `reader3.py`: 核心处理脚本。负责解析 EPUB/PDF 文件，提取章节内容和元数据，并将其序列化存储到本地目录。支持命令行参数指定输出目录。
- `server.py`: Web 服务器。基于 FastAPI，提供书籍列表、上传接口和阅读界面。
- `templates/`: 存放 HTML 模板文件（`library.html`, `reader.html`）。
- `epub_resource/`: 存放用户上传的原始 EPUB/PDF 文件。
- `epub_parse_data/`: 存放解析后的书籍数据（Pickle 文件和图片资源）。
- `requirements.txt`: 项目依赖列表。

## 项目依赖

本项目依赖以下 Python 包：
- `beautifulsoup4`: HTML 解析
- `ebooklib`: EPUB 处理
- `pymupdf`: PDF 处理
- `fastapi`: Web 框架
- `jinja2`: 模板引擎
- `uvicorn`: ASGI 服务器
- `python-multipart`: 处理文件上传

详细依赖见 `requirements.txt`。

## Usage (使用说明)

### 方式一：使用 uv (推荐)

本项目使用 [uv](https://docs.astral.sh/uv/)。例如，将 [my_book]下载到此目录并重命名为 `my_book.epub`，然后运行：

```bash
uv run reader3.py my_book.epub
```

这将创建 `my_book_data` 目录，从而将书籍注册到您的本地书库。然后我们可以运行服务器：

```bash
uv run server.py
```

### 方式二：使用 pip (标准 Python 环境)

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 启动服务器：
   ```bash
   python server.py
   ```
   
   启动后，可以直接在浏览器中上传书籍。

3. (可选) 手动处理书籍：
   ```bash
   python reader3.py my_book.epub
   ```

### 方式三：使用 Conda (虚拟环境)

1. 创建并激活虚拟环境：
   ```bash
   conda create -n epub python=3.13
   conda activate epub
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 启动服务器：
   ```bash
   python server.py
   ```

## 功能特性

- **EPUB/PDF 上传**：在 Library 页面直接上传 EPUB 或 PDF 文件，自动解析并添加到书架。
- **目录导航**：支持复杂的 EPUB/PDF 目录跳转。
- **阅读状态保持**：刷新页面或跳转目录后，侧边栏滚动位置保持不变。
- **侧边栏折叠**：支持隐藏/显示侧边栏，提供沉浸式阅读体验。
- **资源管理**：自动提取 EPUB/PDF 中的图片资源（包括封面），并处理路径引用。

## 项目配置

- 默认端口：8123
- 上传目录：`epub_resource/`
- 数据目录：`epub_parse_data/` (通过 Web 上传时) 或 `*_data` (通过 CLI 运行时默认)

## License

MIT

## 变更记录

- 2025-12-30:
    - 新增 PDF 支持：支持上传、解析（基于 PyMuPDF）和阅读 PDF 文件。
    - 修复 EPUB 封面图片加载问题（增强 SVG/xlink 兼容性）。
    - 新增 Web 端 EPUB/PDF 上传功能，支持自动解析。
    - 优化文件存储结构：新增 `epub_resource` 和 `epub_parse_data` 目录。
    - 增加侧边栏折叠功能。
    - 优化侧边栏滚动体验（状态保持）。
    - 修复目录跳转路径问题（支持 URL 编码路径）。
    - 添加 requirements.txt，完善 README.md 文档（项目架构、依赖、启动方式）。
