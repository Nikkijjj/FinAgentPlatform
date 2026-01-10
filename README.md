# 智能个性化盯盘系统 - 前端

<div align="center">

[![Vue 3](https://img.shields.io/badge/Vue-3.4%2B-brightgreen)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.0%2B-yellow)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Agent驱动的个性化投资盯盘系统前端实现**

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

<div align="center">

[![Vue 3](https://img.shields.io/badge/Vue-3.4%2B-brightgreen)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.0%2B-yellow)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**An Agent-Powered Personalized Investment Monitoring System Frontend**

</div>

---

## 📖 Project Overview

The Intelligent Personalized Stock Monitoring System is an innovative investment assistant platform based on the "User-Driven + AI-Assisted" design philosophy. The system fundamentally solves the pain points of traditional monitoring systems (high professional barriers, complex operations) and emerging intelligent financial assistants (lack of personalization) through **natural language interaction** and **AI intelligent planning**.

This project is the frontend implementation, built with **Vue 3 + TypeScript + Vite**, providing an intuitive, efficient, and scalable user interface that enables users to easily customize investment goals, manage portfolios, receive intelligent analysis reports, and get real-time alerts.

### 🎯 Core Innovations

- **Zero-Barrier Requirement Input**: Describe investment goals in natural language, no manual configuration of complex indicators
- **Intelligent Rule Generation**: AI automatically converts requirements into executable monitoring rules
- **Personalized Report Customization**: Supports custom report frameworks, content dimensions, and push frequencies
- **Real-Time Event Monitoring**: Minute-level market data monitoring with instant alert triggers
- **Multi-Agent Collaboration**: Four analysis agents (macro, industry, stock, sentiment) working intelligently together

---

## ✨ Core Features

### 1️⃣ User Personalized Requirements Management
- **Investment Goal Setting**: Multi-dimensional configuration including annualized return rate, investment horizon, risk tolerance
- **Portfolio Management**: Visual portfolio stock management with batch import and real-time P&L calculation
- **Watchlist Monitoring**: Custom group management (focus pool, to-buy pool, holding pool, to-sell pool)
- **Information Dimension Preferences**: Flexible configuration of information dimensions to follow (PE, revenue growth, industry policies, etc.)

### 2️⃣ Intelligent Watch Rule Generation
- **AI-Assisted Generation**: Automatically generates monitoring rules based on user investment goals and positions
- **Rule Visualization**: Clear display of monitoring indicators, trigger conditions, and priority levels
- **Intelligent Threshold Recommendation**: Provides scientific threshold suggestions based on historical data and industry averages
- **Real-Time Rule Validation**: Prevents rule conflicts and ensures logical consistency

### 3️⃣ Personalized Reporting System
- **Report Template Library**: Built-in daily, weekly, monthly, and other standard templates
- **Custom Framework Builder**: Drag-and-drop interface for customizing report sections and order
- **Multi-Dimensional Analysis**: Integrates comprehensive analysis of macro, industry, stock, and sentiment
- **Smart Chart Generation**: Automatically generates trend charts, comparison graphs, heatmaps, and other visualizations
- **Multi-Format Export**: Supports HTML, PDF, Excel formats

### 4️⃣ Real-Time Alerts & Push Notifications
- **Multiple Alert Types**: Rule-triggered alerts, manual alerts, system notifications
- **Multi-Channel Push**: WebSocket real-time push, email reminders, SMS notifications (requires configuration)
- **Read Status Management**: Clear notification management with read/unread status tracking
- **Historical Record Tracking**: Complete alert history records with traceability

### 5️⃣ Intelligent Analysis Dashboard
- **Market Overview**: Real-time market summary, hot event list
- **In-Depth Stock Analysis**: PE/PB percentile, financial indicators, sentiment analysis
- **Industry Prosperity Index**: Industry scoring based on revenue growth, profit margin, and policy impact
- **Sentiment Index**: Comprehensive sentiment score combining news, capital flow, and forum heat

---

## 🛠️ Technical Architecture

### Frontend Technology Stack

| Category | Technology | Version | Application Scenario |
|----------|------------|---------|---------------------|
| Frontend Framework | Vue.js | 3.4+ | Core view layer, developed with Composition API |
| Build Tool | Vite | 5.0+ | Project building, dev server, packaging optimization |
| Type System | TypeScript | 5.0+ | Global type constraints, improved code maintainability |
| Routing | Vue Router | 4.2+ | Page routing, permission interception, lazy loading |
| State Management | Pinia | 2.1+ | Global state management (user info, permissions, config) |
| HTTP Client | Axios | 1.6+ | API request encapsulation, interceptors, error handling |
| CSS Preprocessor | SCSS | 1.6+ | Global style variables, modular styles, style reuse |
| Code Linting | ESLint + Prettier | 8.0+/3.0+ | Code syntax validation, unified formatting |
| UI Library (Optional) | Element Plus | 2.4+ | Basic UI components (buttons, forms, tables) for rapid development |

---

## 🚀 Quick Start

### Environment Requirements

- Node.js: `>= 18.0.0`
- npm/pnpm: `>= 8.0.0`
- Modern browsers (Chrome 90+, Firefox 90+, Safari 14+)

### Install Dependencies

```bash
# Clone the project
git clone https://github.com/your-username/intelligent-stock-monitor-frontend.git
cd intelligent-stock-monitor-frontend

# Install dependencies (pnpm recommended)
pnpm install

# Or use npm
npm install
```

### Development

```bash
# Start development server
pnpm dev

# Application will run at http://localhost:3000
```

### Production Build

```bash
# Production build
pnpm build

# Output in dist/ directory
```

### Code Linting & Formatting

```bash
# ESLint check
pnpm lint

# Prettier format
pnpm format
```

---

## ⚙️ Environment Configuration

The project supports multi-environment configuration, with config files in the project root:

```bash
.env.development        # Development environment
.env.test              # Test environment
.env.production        # Production environment
```

### Core Configuration Items

```env
# API base URL
VITE_API_BASE_URL=http://localhost:5000/api

# WebSocket URL
VITE_WS_BASE_URL=ws://localhost:5000/ws

# Application title
VITE_APP_TITLE=Intelligent Stock Monitor

# Enable mock data (development)
VITE_USE_MOCK=true

# Default language
VITE_DEFAULT_LANGUAGE=en-US

# Log level
VITE_LOG_LEVEL=info
```

---

## 🎨 Development Guidelines

### Code Standards

- Use **ESLint** for syntax validation
- Use **Prettier** for unified code formatting
- Use **Husky** + **lint-staged** for pre-commit validation

### Git Commit Convention

```
feat: New feature
fix: Bug fix
docs: Documentation update
style: Code style adjustment
refactor: Code refactoring
test: Test-related changes
chore: Build or tooling changes
```

### Component Development Guidelines

1. **Basic Components**: No business logic, high reusability, clear props interface
2. **Business Components**: Encapsulate specific business logic, data-cohesive
3. **Layout Components**: Handle overall page layout, responsive design support

Example:
```vue
<template>
  <div class="monitor-card">
    <header class="monitor-card__header">
      <h3>{{ title }}</h3>
    </header>
    <main class="monitor-card__body">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string;
}

defineProps<Props>();
</script>

<style scoped lang="scss">
.monitor-card {
  // BEM naming convention
  &__header {
    padding: 16px;
  }
}
</style>
```

---

## 📊 Performance Optimization

- **Code Splitting**: Vite automatically splits code by modules for on-demand loading
- **Component Lazy Loading**: Route-level components are automatically lazy-loaded
- **Image Optimization**: WebP format support with automatic compression
- **Caching Strategy**: Long-term caching for static resources, reasonable caching for API data
- **CDN Acceleration**: Use CDN for large dependencies (Vue, Element Plus) in production

---

## 🔒 Security Features

- **XSS Protection**: Automatic escaping of user input content
- **CSRF Protection**: Token-based request validation
- **Data Desensitization**: Automatic desensitization of sensitive data in logs and UI
- **Permission Control**: Route-level and button-level permission control
- **HTTPS Enforcement**: Force HTTPS access in production environment

---

## 🌐 Browser Support

| Browser | Minimum Version |
|---------|-----------------|
| Chrome | 90+ |
| Firefox | 90+ |
| Safari | 14+ |
| Edge | 90+ |

---

## 🤝 Contributing

Welcome to contribute code, report issues, and suggest improvements!

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: Add new feature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

---

<div id="中文"></div>

*[View Chinese Version](#中文)*

---
