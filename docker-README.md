# Docker 部署指南

本文档提供了使用 Docker 部署 Cotex AI Agent 应用的详细说明。

## 前提条件

- 安装 [Docker](https://docs.docker.com/get-docker/)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/) (可选，但推荐)

## 使用 Docker 部署

### 方法一：使用 Docker Compose (推荐)

1. 在项目根目录下运行以下命令构建并启动容器：

```bash
docker-compose up -d
```

2. 查看容器日志：

```bash
docker-compose logs -f
```

3. 停止并移除容器：

```bash
docker-compose down
```

### 方法二：直接使用 Docker 命令

1. 构建 Docker 镜像：

```bash
docker build -t cotex-ai-agent .
```

2. 运行容器：

```bash
docker run -d --name cotex-ai-agent \
  -p 8001:8001 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/outputs:/app/outputs \
  cotex-ai-agent
```

3. 查看容器日志：

```bash
docker logs -f cotex-ai-agent
```

4. 停止并移除容器：

```bash
docker stop cotex-ai-agent
docker rm cotex-ai-agent
```

## 环境变量

可以通过环境变量自定义应用的行为：

- `PORT`: 应用监听的端口号（默认：8001）

## 数据卷

应用使用以下数据卷：

- `./data:/app/data`: 存储输入数据
- `./outputs:/app/outputs`: 存储分析结果和报告

## 访问应用

应用启动后，可以通过以下地址访问：

- API 接口：http://localhost:8001

## 注意事项

- 确保 `data` 目录中包含必要的输入数据
- 分析结果将保存在 `outputs` 目录中
- 如需修改端口映射，请编辑 `docker-compose.yml` 文件中的 `ports` 部分