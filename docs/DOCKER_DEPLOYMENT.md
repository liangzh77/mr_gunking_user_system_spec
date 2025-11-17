  让我们在生产服务器上执行完整的重启流程：

  cd /opt/mr_gunking_user_system_spec

  # 1. 拉取最新代码
  git pull origin 001-mr-v2

  # 2. 停止所有容器
  docker-compose down

  # 3. 重新构建backend和frontend镜像（--no-cache确保使用最新代码）
  docker-compose build backend frontend

  # 4. 启动所有服务
  docker-compose up -d

  # 5. 执行数据库迁移
  docker-compose exec backend alembic upgrade head

  # 6. 查看服务状态
  docker-compose ps

  # 7. 查看backend启动日志，确认路由注册成功
  docker-compose logs backend | grep -i "router\|startup\|application_ready"


  # 重启backend
  docker-compose up -d --force-recreate backend

  # 查看backend启动日志
  docker logs mr_game_ops_backend --tail 50

  关键点：
  - docker-compose build --no-cache 强制重新构建，不使用缓存
  - docker-compose down 确保旧容器完全停止
  - docker-compose up -d 使用新镜像启动

  执行完后，再测试一下：
  curl -k https://mrgun.chu-jiao.com/health