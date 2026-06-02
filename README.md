# Industry Reports / 行业报告聚合站

A self-updating industry reports hub powered by Quark Drive. Syncs report data automatically and renders a searchable dashboard via GitHub Pages.

行业报告聚合站 — 基于夸克网盘数据源，自动同步行业报告，通过 GitHub Pages 提供可搜索、可分类的浏览体验。

🌐 **Live Site / 线上地址**: [nyctocereusnicola.github.io/industry-reports](https://nyctocereusnicola.github.io/industry-reports/)

---

## Features / 功能

- **Search / 智能搜索** — Real-time search by title, tags, and summary / 按标题、标签、摘要实时搜索
- **Filter / 分类筛选** — Filter by 20+ industry categories / 覆盖 20+ 行业分类筛选
- **One-click Access / 一键跳转** — Direct link to Quark Drive source file / 一键跳转夸克网盘源文件
- **Auto Sync / 自动同步** — GitHub Actions keeps data fresh / GitHub Actions 自动更新数据
- **Dashboard / 统计面板** — Report count, category stats at a glance / 报告总数、分类数一目了然
- **Responsive / 响应式** — PC, tablet, and mobile friendly / 完美适配 PC / 平板 / 手机

## Architecture / 架构

```
┌──────────────────────────────────────────────────┐
│  Quark Drive (夸克网盘)                            │
│  └─ 行业报告文件夹（20+ 分类）                      │
├──────────────────────────────────────────────────┤
│  scan_quark.py                                    │
│  ├─ Cookie 认证扫描夸克网盘                        │
│  ├─ 递归遍历子文件夹                                │
│  ├─ 从文件名自动提取年份和分类                      │
│  ├─ 生成 docs/quark/data/categories/*.json        │
│  └─ 输出格式兼容前端渲染                            │
├──────────────────────────────────────────────────┤
│  GitHub Pages                                     │
│  └─ docs/quark/index.html                         │
│     纯静态前端，读取 JSON 数据渲染                  │
└──────────────────────────────────────────────────┘
```

## Categories / 覆盖分类

美妆个护、香氛、快消零售、食品饮料、品牌手册、大健康、母婴亲子、宠物经济、家居生活、户外运动、服饰时尚、奢侈品、小红书、抖音、TikTok、跨境电商、营销方案、及其他

## Quick Start / 快速开始

### Prerequisites / 环境要求

- Python 3.11+
- Quark Drive account with industry reports / 夸克网盘账号及报告文件

### Local Setup / 本地运行

```bash
# Clone the repo / 克隆仓库
git clone https://github.com/nyctocereusnicola/industry-reports.git
cd industry-reports

# Install dependencies / 安装依赖
pip install -r requirements.txt

# Set up environment variables / 配置环境变量
cp .env.example .env
# Edit .env with your Quark cookie / 填入夸克网盘 Cookie

# Run scan / 运行扫描（生成分类 JSON）
python scan_quark.py

# Preview / 浏览器打开 docs/quark/index.html 预览
```

### Deploy to GitHub Pages / 部署到 GitHub Pages

#### 1. Push to your GitHub repo / 推送到 GitHub

#### 2. Set GitHub Secrets / 配置 GitHub Secrets

**Settings → Secrets and variables → Actions → New repository secret**

前往 **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Description / 说明 |
|--------|-------------------|
| `QUARK_COOKIE` | Quark Drive cookie / 夸克网盘 Cookie |
| `QUARK_ROOT_FID` | Root folder ID / 根文件夹 FID |

> ⚠️ **Never commit secrets to your repo / 切勿将密钥提交到仓库**

#### 3. Enable GitHub Pages / 启用 GitHub Pages

**Settings → Pages** → Source: `Deploy from a branch` → Branch: `main` / `/docs`

## Project Structure / 项目结构

```
industry-reports/
├── docs/                              # GitHub Pages site / 站点文件
│   ├── index.html                     # Main dashboard / 主页面
│   └── quark/                         # Quark Drive section / 夸克网盘版块
│       ├── index.html                 # Quark dashboard page / 夸克报告页面
│       └── data/
│           └── categories/             # Category JSON files / 分类数据（自动生成）
│               ├── 美妆个护.json
│               ├── 食品饮料.json
│               ├── 跨境电商.json
│               └── ...
├── scan_quark.py                       # Quark Drive scanner / 夸克网盘扫描脚本
├── enrich_data.py                      # Data enrichment & dedup / 数据增强与去重
├── database.py                          # Database utilities / 数据库工具
├── .github/workflows/
│   └── sync.yml                        # CI/CD workflow / 自动同步工作流
├── requirements.txt                    # Python dependencies / Python 依赖
└── .env.example                        # Env template / 环境变量模板
```

## Tech Stack / 技术栈

| Layer / 层 | Tech / 技术 |
|-----------|------------|
| Frontend / 前端 | Vanilla HTML + CSS + JS (no framework / 零框架) |
| Scanner / 扫描 | Python 3.11, httpx |
| Data / 数据 | JSON (flat files / 扁平文件) |
| CI/CD | GitHub Actions |
| Hosting / 托管 | GitHub Pages |
| Data Source / 数据源 | Quark Drive (夸克网盘) |

## Author / 作者

Created by [Nicola Chen](https://github.com/nyctocereusnicola) — Been through finance, branding, marketing, and cross-border commerce. Obsessed with brands and markets, drawn to interesting things, builds with attitude and personality. Serving global markets.

扎过金融、品牌、营销、跨境这几个坑。对品牌和市场有执念，喜欢有趣的玩意，做有态度有个性的东西。服务全球市场。

## License / 许可证

MIT License — free to use, modify, and distribute with attribution.
MIT 许可证 — 自由使用、修改和分发，需保留署名。
