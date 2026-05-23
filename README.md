# 📊 行业报告集合站

> 搜索浏览行业洞察报告，一键跳转飞书查看完整源文件
> 
> 🌐 **线上地址**: https://nyctocereusnicola.github.io/industry-reports/

## 🎯 功能

- **🔍 智能搜索** — 按标题、标签、摘要实时搜索
- **🏷️ 分类筛选** — 按行业分类快速过滤
- **🔗 飞书跳转** — 一键跳转到飞书源文件
- **🔄 自动同步** — GitHub Actions 每 30 分钟自动同步飞书文件夹
- **📊 统计面板** — 报告总数、分类数等一目了然
- **📱 响应式** — 完美适配 PC / 平板 / 手机

## 🏗 架构

```
┌─────────────────────────────────────────────┐
│  GitHub Actions (每30分钟自动运行)            │
│  ├─ sync_reports.py                         │
│  ├─ 调用飞书 API 获取文件列表                │
│  ├─ 生成 docs/data/reports.json             │
│  └─ 自动提交到仓库                           │
├─────────────────────────────────────────────┤
│  GitHub Pages                               │
│  └─ docs/index.html 纯静态前端              │
│     └─ 读取 reports.json 渲染页面            │
└─────────────────────────────────────────────┘
```

## 🚀 快速开始

### 本地运行

```bash
# 安装依赖
pip install httpx

# 运行同步脚本（生成 reports.json）
python sync_reports.py

# 浏览器打开 docs/index.html 即可预览
```

### 部署到 GitHub Pages

#### 1. 创建 GitHub 仓库 & 推送代码

```powershell
# 在项目目录下
git init
git add .
git commit -m "初始化行业报告集合站"
git branch -M main
git remote add origin https://github.com/nyctocereusnicola/industry-reports.git
git push -u origin main
```

#### 2. 设置 GitHub Secrets

在 GitHub 仓库页面: **Settings → Secrets and variables → Actions → New repository secret**

添加三个密钥:

| Name | Value |
|------|-------|
| `FEISHU_APP_ID` | `cli_aa9bf80b5678dbee` |
| `FEISHU_APP_SECRET` | `BSrMFRLJSEOv9cngkERqEcg83IRbj2oi` |
| `FEISHU_FOLDER_TOKEN` | `YYLHfvuCylpAQVdzTRxcdDpgnyc` |

#### 3. 启用 GitHub Pages

在 GitHub 仓库页面: **Settings → Pages**

- **Source**: Deploy from a branch
- **Branch**: `main` / `/docs`
- 点击 **Save**

等待 1-2 分钟后，访问:
```
https://nyctocereusnicola.github.io/industry-reports/
```

## 📁 项目结构

```
├── docs/                     # GitHub Pages 站点
│   ├── index.html            # 前端页面（纯静态）
│   └── data/
│       └── reports.json      # 报告数据（自动同步生成）
├── sync_reports.py           # 飞书同步脚本
├── .github/workflows/
│   └── sync.yml              # 定时 + 手动同步工作流
├── .env.example              # 环境变量模板
├── .gitignore                # Git 忽略规则
└── .env                      # 本地环境变量（不提交到 Git）
```

## 🔧 飞书配置

1. [飞书开放平台](https://open.feishu.cn/app) → 创建企业自建应用
2. 获取 **App ID** 和 **App Secret**
3. 添加权限: `drive:drive` 或 `drive:file:readonly`
4. 发布应用并审批通过
5. 在飞书中将报告文件夹共享给该应用
6. 从文件夹 URL 中提取 `folder_token`

## 📝 许可证

MIT
