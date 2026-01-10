# 智能个性化盯盘系统 - 前端

<div align="center">

[![Vue 3](https://img.shields.io/badge/Vue-3.4%2B-brightgreen)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.0%2B-yellow)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**AI驱动的个性化投资盯盘系统前端实现**

[English](#english) | [中文](#中文)

</div>

---

## 📖 项目简介

智能个性化盯盘系统是一款基于"用户主导 + 智能辅助"理念设计的创新型投资辅助平台。系统通过**自然语言交互**和**AI智能规划**，彻底解决传统盯盘系统专业门槛高、操作复杂，以及新兴智能理财助理缺乏个性化支持的痛点。

本项目是系统的前端实现，采用**Vue 3 + TypeScript + Vite**技术栈构建，提供直观、高效、可扩展的用户界面，支持用户便捷定制投资目标、管理持仓、接收智能分析报告和实时预警。

### 🎯 核心创新点

- **零门槛需求输入**：自然语言描述投资目标，无需手动配置复杂指标
- **智能规则生成**：AI自动将需求转化为可执行的盯盘规则
- **个性化报告定制**：支持自定义报告框架、内容维度和推送频率
- **实时事件监测**：分钟级行情监控，即时触发预警提醒
- **多Agent协同**：宏观、行业、个股、情绪四大分析Agent智能协作

---

## ✨ 核心功能特性

### 1️⃣ 用户个性化需求管理
- **投资目标设定**：支持年化收益率、投资期限、风险容忍度等多维度配置
- **持仓管理**：可视化持仓股管理，支持批量导入和实时盈亏计算
- **自选股监控**：自定义分组管理（关注池、待买池、持仓池、待卖池）
- **信息维度偏好**：灵活配置关注的信息维度（PE、营收增速、行业政策等）

### 2️⃣ 智能盯盘规则生成
- **AI辅助生成**：基于用户投资目标和持仓情况，自动生成盯盘规则
- **规则可视化**：清晰展示监控指标、触发条件和优先级
- **阈值智能推荐**：结合历史数据和行业均值，提供科学的阈值建议
- **实时规则校验**：避免规则冲突，确保逻辑合理性

### 3️⃣ 个性化报告系统
- **报告模板库**：内置日报、周报、月报等多种标准模板
- **自定义框架**：支持拖拽式定制报告章节和顺序
- **多维度分析**：集成宏观、行业、个股、情绪全方位分析
- **智能图表生成**：自动生成趋势图、对比图、热力图等可视化图表
- **多格式导出**：支持HTML、PDF、Excel格式导出

### 4️⃣ 实时预警与推送
- **多种提醒类型**：规则触发提醒、手动设置提醒、系统推送
- **多渠道推送**：支持WebSocket实时推送、邮件提醒、短信通知（需配置）
- **已读状态管理**：清晰的提醒消息管理和已读/未读状态跟踪
- **历史记录追溯**：完整的提醒历史记录，支持回溯查询

### 5️⃣ 智能分析看板
- **市场总览**：实时行情汇总、热门事件列表
- **个股深度分析**：PE/PB分位、财务指标、舆情情绪综合展示
- **行业景气度**：基于营收增速、利润率、政策影响的行业评分
- **情绪指数**：融合舆情、资金流向、论坛热度的综合情绪得分

---

## 🛠️ 技术架构

### 前端技术栈

| 技术类别 | 技术选型 | 版本 | 应用场景 |
|---------|---------|------|---------|
| 前端框架 | Vue.js | 3.4+ | 核心视图层，基于 Composition API 开发 |
| 构建工具 | Vite | 5.0+ | 项目构建、开发服务、打包优化 |
| 类型系统 | TypeScript | 5.0+ | 全局类型约束，提升代码可维护性 |
| 路由管理 | Vue Router | 4.2+ | 页面路由控制、权限拦截、路由懒加载 |
| 状态管理 | Pinia | 2.1+ | 全局状态管理（用户信息、权限、配置） |
| 网络请求 | Axios | 1.6+ | 接口请求封装、拦截器、错误统一处理 |
| 样式预编译 | SCSS | 1.6+ | 全局样式变量、模块化样式、样式复用 |
| 代码规范 | ESLint + Prettier | 8.0+/3.0+ | 代码语法校验、格式统一 |
| UI 组件库 | Element Plus | 2.4+ | 基础 UI 组件快速开发 |

## 🚀 快速开始

### 环境要求

- Node.js: `>= 18.0.0`
- npm/pnpm: `>= 8.0.0`
- 现代浏览器（Chrome 90+, Firefox 90+, Safari 14+）

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/your-username/intelligent-stock-monitor-frontend.git
cd intelligent-stock-monitor-frontend

# 安装依赖（推荐pnpm）
pnpm install

# 或使用npm
npm install
```

### 开发环境运行

```bash
# 启动开发服务器
pnpm dev

# 应用将在 http://localhost:3000 运行
```

### 构建生产版本

```bash
# 生产环境构建
pnpm build

# 输出在 dist/ 目录
```

### 代码检查与格式化

```bash
# ESLint检查
pnpm lint

# Prettier格式化
pnpm format
```

---

## ⚙️ 环境配置

项目支持多环境配置，配置文件位于项目根目录：

```bash
.env.development        # 开发环境
.env.test              # 测试环境
.env.production        # 生产环境
```

### 核心配置项

```env
# API基础地址
VITE_API_BASE_URL=http://localhost:5000/api

# WebSocket地址
VITE_WS_BASE_URL=ws://localhost:5000/ws

# 应用标题
VITE_APP_TITLE=智能盯盘系统

# 是否开启Mock数据（开发环境）
VITE_USE_MOCK=true

# 默认语言
VITE_DEFAULT_LANGUAGE=zh-CN

# 日志级别
VITE_LOG_LEVEL=info
```

---

## 📊 性能优化

- **代码分割**：Vite自动按模块拆分，按需加载
- **组件懒加载**：路由级组件自动懒加载
- **图片优化**：支持WebP格式，自动压缩
- **缓存策略**：静态资源长期缓存，接口数据合理缓存
- **CDN加速**：生产环境使用CDN引入大型依赖（Vue、Element Plus）

---

## 🔒 安全特性

- **XSS防护**：用户输入内容自动转义
- **CSRF防护**：请求携带Token验证
- **敏感数据脱敏**：日志和界面中自动脱敏处理
- **权限控制**：路由级和按钮级权限控制
- **HTTPS强制**：生产环境强制HTTPS访问

---

## 🤝 贡献指南

欢迎贡献代码、提出问题和建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: 添加新功能'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

<div id="english"></div>

## 🌟 English Version

# Intelligent Personalized Stock Monitor - Frontend

An AI-powered personalized stock monitoring system that revolutionizes traditional trading by combining natural language interaction with intelligent planning. The frontend is built with Vue 3 + TypeScript + Vite, providing an intuitive interface for customizing investment goals, managing portfolios, and receiving AI-generated reports and real-time alerts.

## ✨ Key Features

- **Natural Language Input**: Describe investment goals conversationally, no complex configuration needed
- **AI Rule Generation**: Automatically converts user needs into executable monitoring rules
- **Custom Report Builder**: Drag-and-drop interface for personalized report templates
- **Real-time Event Monitoring**: Minute-level market data tracking with instant alerts
- **Multi-Agent Collaboration**: Macro, industry, stock, and sentiment analysis agents working together

[View full documentation](#中文)

---

<div id="中文"></div>

*返回中文版本*

---
