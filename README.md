# 听音审美知识专栏 - 后端API系统

## 功能概述

本后端系统已全面升级，支持以下功能：

### 1. 用户实名管理
- 记录用户飞书账号名字
- 生成唯一用户ID
- 追踪用户所有操作

### 2. 答题积分系统
- 每答对一题获得10分
- 实时统计用户答题情况
- 记录详细答题历史

### 3. 数据统计功能
- 用户积分排行榜
- 答题记录详情（用户名、选择答案、正确与否）
- 总体数据统计（参与人数、答题数、正确率等）
- 评论互动统计

### 4. 管理后台
- 可视化数据展示
- 实时刷新功能
- 中文界面，简洁易用

## 启动方式

1. 确保已安装依赖：
```bash
pip install -r requirements.txt
```

2. 启动后端服务：
```bash
python -m uvicorn main:app --reload --port 8000
```

或者直接运行：
```bash
start.bat
```

## 访问地址

- **API文档**: http://localhost:8000/docs
- **管理后台**: http://localhost:8000/admin
- **健康检查**: http://localhost:8000/health

## API接口说明

### 评论相关
- `POST /api/comments` - 创建评论（需要userName）
- `GET /api/comments` - 获取所有评论
- `POST /api/comments/like` - 点赞评论

### 答题相关
- `GET /api/quizzes/{quiz_id}` - 获取问题详情
- `POST /api/quizzes/answer` - 提交答案（需要userName和userId）
- `GET /api/quizzes/{quiz_id}/stats` - 获取问题统计

### 数据统计
- `GET /api/stats/overview` - 总体数据统计
- `GET /api/stats/users` - 用户积分排行榜
- `GET /api/stats/quiz-records` - 所有答题记录
- `GET /api/stats/comments` - 评论统计

## 数据结构

### 答题记录格式
```json
{
  "userName": "张三",
  "quizId": "quiz_1",
  "selectedOption": "B",
  "isCorrect": true,
  "time": "14:30",
  "timestamp": "2025-12-12T14:30:00"
}
```

### 用户积分格式
```json
{
  "rank": 1,
  "userName": "张三",
  "score": 100,
  "correct": 10,
  "wrong": 2,
  "total": 12,
  "accuracy": 83.33
}
```

## 管理后台功能

访问 http://localhost:8000/admin 可以查看：

1. **实时统计卡片**
   - 参与用户总数
   - 评论总数
   - 答题总数
   - 整体正确率

2. **答题详细记录表格**
   - 显示所有用户的答题记录
   - 包含用户名、选择答案、答题结果、时间
   - 支持手动刷新和自动刷新（30秒）

3. **用户积分排行榜**
   - 按积分排序
   - 显示正确数、错误数、正确率
   - 前三名特殊标记

## 注意事项

1. 当前使用内存存储，重启服务后数据会丢失
2. 生产环境建议使用数据库（如PostgreSQL、MySQL）
3. CORS已配置为允许所有域名，生产环境应限制具体域名
4. 答题正确每题+10分，错误不扣分

## 技术栈

- FastAPI - Web框架
- Pydantic - 数据验证
- Uvicorn - ASGI服务器
