# Ansible UI - 现代化 Ansible 自动化管理平台

一个功能强大的 Web 界面 Ansible 自动化管理平台，为运维团队提供直观、高效的主机管理、命令执行、文件传输和云资源管理解决方案。

![Ansible UI](https://img.shields.io/badge/Ansible-UI-blue?style=for-the-badge&logo=ansible)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-teal?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-19-blue?style=for-the-badge&logo=react)

## ✨ 核心功能

### 🔧 主机管理
- 统一管理所有 Ansible 受管主机
- 支持 SSH 密钥和密码认证
- 主机分组和标签管理
- 实时主机状态监控

### 🚀 Ansible 执行
- 可视化执行 Ansible Ad-hoc 命令
- Playbook 管理和执行
- 实时任务执行监控
- 执行结果分析和日志查看


### 🖥️ 终端管理
- WebSocket 实时终端
- 多终端会话支持
- 终端日志记录
- 命令历史记录

### ☁️ 腾讯云集成
- 腾讯云主机管理
- 云主机批量操作
- 资源监控和统计

### 📊 监控与日志
- 访问日志记录
- 执行历史追踪
- 实时日志查看
- 性能监控

## 🏗️ 技术架构

### 后端技术栈
- **FastAPI** - 现代化的 Python Web 框架
- **SQLite** - 轻量级数据库
- **WebSocket** - 实时通信
- **JWT** - 身份认证
- **Ansible** - 自动化引擎

### 前端技术栈
- **React 19** - 用户界面库
- **TypeScript** - 类型安全的 JavaScript
- **Ant Design Pro** - 企业级 UI 框架
- **xterm.js** - Web 终端组件
- **UmiJS** - 企业级 React 应用框架

## 📋 系统要求

- **Python**: 3.8+
- **Node.js**: 20.0.0+
- **操作系统**: Linux/macOS (Windows 需 WSL)
- **内存**: 建议 2GB+
- **存储**: 建议 10GB+

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd ansible-ui

# 创建虚拟环境并安装 Python 依赖
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. 配置系统

```bash
# 编辑配置文件
vim config.yaml
```

配置示例：
```yaml
admin:
  username: admin
  password: admin123

enable_login: true

tencent:
  secret_id: "your_secret_id"
  secret_key: "your_secret_key"
```

### 3. 启动服务

**后端服务**:
```bash
cd app
python main.py
```

**前端服务**:
```bash
cd myapp
npm install
npm run dev
```

### 4. 访问系统

打开浏览器访问 http://localhost:3000，使用管理员账户登录。

## 📖 使用说明

### 添加主机
1. 进入"主机管理"页面
2. 点击"添加主机"
3. 填写主机信息：主机地址、SSH 认证信息、主机分组
4. 保存配置

### 执行 Ansible 命令
1. 进入"Ansible 执行"页面
2. 选择目标主机
3. 输入要执行的命令
4. 点击执行并查看结果

### 使用终端
1. 进入"终端管理"页面
2. 选择要连接的主机
3. 启动终端会话
4. 在终端中执行命令

### 文件传输
1. 进入"文件管理"页面
2. 选择源和目标主机
3. 上传或下载文件
4. 查看传输进度

## 🔧 配置说明

### 管理员配置
```yaml
admin:
  username: admin          # 管理员用户名
  password: admin123       # 管理员密码
```

### 腾讯云配置
```yaml
tencent:
  secret_id: ""            # 腾讯云 SecretId
  secret_key: ""           # 腾讯云 SecretKey
```

### 登录功能控制
```yaml
enable_login: true         # 是否启用登录功能
```



## 🔒 安全注意事项

1. **生产环境配置**
   - 修改默认管理员密码
   - 使用强密码和密钥
   - 配置 HTTPS

2. **网络安全**
   - 配置防火墙规则
   - 使用 SSH 密钥认证
   - 定期更新密码

3. **数据安全**
   - 定期备份数据库
   - 加密敏感信息
   - 限制文件上传类型


### 日志查看
- 应用日志: `logs/app.log`
- 访问日志: 通过 API 查看 `/api/access-logs`
- 错误日志: 检查控制台输出


## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [ansible-ui](https://github.com/sky22333/ansible-ui) - Ansible Web管理面板


---

**注意**: 本项目目前主要支持 Linux 和 macOS 系统，Windows 用户建议使用 WSL 或 Docker 运行。