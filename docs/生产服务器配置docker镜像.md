阿里云镜像加速器（最推荐，因为你用的是阿里云服务器）

在生产服务器（阿里云 Linux）上配置：

# 1. 创建或编辑 Docker 配置文件
sudo mkdir -p /etc/docker

# 2. 编辑配置文件
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.1panel.live",
    "https://hub.rat.dev",
    "https://docker.chenby.cn",
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://docker.nju.edu.cn"
  ]
}
EOF

# 3. 重启 Docker 服务
sudo systemctl daemon-reload
sudo systemctl restart docker