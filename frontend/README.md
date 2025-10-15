# MR游戏运营管理系统 - 前端

基于 Vue 3 + TypeScript + Vite + Element Plus 的现代化前端项目。

## 技术栈

- **框架**: Vue 3.4+ (Composition API)
- **语言**: TypeScript 5.3+
- **构建工具**: Vite 5.0+
- **UI 组件库**: Element Plus 2.5+
- **状态管理**: Pinia 2.1+
- **路由**: Vue Router 4.2+
- **HTTP 客户端**: Axios 1.6+
- **图表库**: ECharts 5.4+ + vue-echarts 6.6+
- **日期处理**: Day.js 1.11+

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API接口定义
│   ├── assets/           # 静态资源
│   ├── components/       # 公共组件
│   ├── pages/            # 页面组件
│   │   ├── operator/     # 运营商端页面
│   │   ├── admin/        # 管理员端页面
│   │   └── finance/      # 财务端页面
│   ├── router/           # 路由配置
│   ├── stores/           # Pinia状态管理
│   ├── types/            # TypeScript类型定义
│   ├── utils/            # 工具函数
│   ├── App.vue           # 根组件
│   └── main.ts           # 应用入口
├── index.html            # HTML模板
├── package.json          # 依赖配置
├── tsconfig.json         # TypeScript配置
└── vite.config.ts        # Vite配置
```

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173

### 3. 构建生产版本

```bash
npm run build
```

### 4. 预览生产构建

```bash
npm run preview
```

## 开发说明

### API 代理配置

开发环境中,Vite会将 `/v1` 开头的请求代理到后端服务 `http://localhost:8000`。

### 路由结构

- `/operator/login` - 运营商登录
- `/operator/register` - 运营商注册
- `/operator/dashboard` - 仪表盘
- `/operator/recharge` - 在线充值
- `/operator/transactions` - 交易记录
- `/operator/refunds` - 退款管理
- `/operator/invoices` - 发票管理
- `/operator/sites` - 运营点管理
- `/operator/applications` - 已授权应用
- `/operator/usage-records` - 使用记录
- `/operator/statistics` - 统计分析
- `/operator/profile` - 个人中心

### 状态管理

使用 Pinia 管理全局状态:

- `authStore` - 认证状态 (登录/登出/用户信息)
- `operatorStore` - 运营商业务数据 (余额/交易/运营点/统计等)

### HTTP 请求

所有 HTTP 请求通过 `src/utils/http.ts` 的 axios 实例发送,已配置:

- JWT Token 自动注入
- 统一错误处理
- 401 自动跳转登录

## 代码规范

- 使用 ESLint 进行代码检查
- 使用 TypeScript 严格模式
- 组件使用 Composition API + `<script setup>` 语法
- 遵循 Vue 3 官方风格指南

## 浏览器支持

现代浏览器,支持 ES2020+

## 许可证

私有项目
