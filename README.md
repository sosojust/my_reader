# reader 3

![my_reader](my_reader.png)

一个轻量级的、自托管的 EPUB/PDF 阅读器，支持按章节阅读 EPUB 和 PDF 书籍。
来自 karpathy 的项目[reader](https://github.com/karpathy/reader3/)，修改了一些功能，并增加了用户系统。

## 项目架构

- `app/`: 应用核心代码
  - `main.py`: 应用入口
  - `models.py`: 数据库模型
  - `schemas.py`: Pydantic 数据模型
  - `database.py`: 数据库连接
  - `auth.py`: 认证逻辑
  - `config.py`: 配置管理
  - `routers/`: 路由模块
  - `core/`: 核心业务逻辑
- `reader3.py`: 核心解析脚本（遗留/工具脚本）
- `templates/`: HTML 模板
- `schema/`: 数据库 SQL 脚本
- `epub_resource/`: 存放用户上传的原始文件（使用 UUID 重命名存储）
- `epub_parse_data/`: 存放解析后的书籍数据（使用 UUID 目录隔离）
- `.env`: 环境变量配置

## 项目依赖

本项目依赖以下 Python 包：
- `beautifulsoup4`, `ebooklib`, `pymupdf`: 文件解析
- `fastapi`, `uvicorn`, `jinja2`, `python-multipart`: Web 框架
- `sqlalchemy`, `pymysql`: 数据库 ORM 和驱动
- `python-dotenv`: 环境变量
- `passlib[bcrypt]`, `python-jose[cryptography]`: 认证安全

## 快速开始

### 1. 环境准备

确保已安装 Python 3.10+ 和 MySQL 数据库。

```bash
# 创建并激活虚拟环境 (推荐)
conda create -n epub python=3.13
conda activate epub

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置数据库

1. 创建 MySQL 数据库（例如 `my_reader_db`）。
2. 复制 `.env.example` 为 `.env` 并配置数据库连接信息：

```ini
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/my_reader_db
SECRET_KEY=your_secret_key_here
```

3. 初始化数据库表结构：
   执行 `schema/01_init.sql` 中的 SQL 语句创建表。

### 3. 启动服务器

**常规启动：**
```bash
python -m app.main
```
或者
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8123 --reload
```

**一键启动 (Conda 环境)：**
```bash
conda activate epub && uvicorn app.main:app --host 0.0.0.0 --port 8123 --reload
```

访问地址：http://localhost:8123

## 功能特性

- **用户系统**：支持用户注册、登录。
- **权限隔离**：用户只能查看自己上传的书籍。
- **EPUB/PDF 上传**：自动解析并添加到个人书架。
- **文件隔离**：使用 UUID 存储文件，解决同名文件冲突问题。
- **目录导航**：支持复杂的 EPUB/PDF 目录跳转。
- **SVG 矢量阅读**：PDF 使用 SVG 渲染，支持文字选择。

## License

MIT
