from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

app = FastAPI(title="听音审美知识专栏 API", version="1.0.0")

# CORS 配置 - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 数据模型 ====================

class Comment(BaseModel):
    """评论模型"""
    id: str = Field(default_factory=lambda: f"comment_{uuid.uuid4().hex[:12]}")
    userName: str
    content: str
    time: str
    likes: int = 0
    liked: bool = False

class CommentCreate(BaseModel):
    """创建评论请求模型"""
    userName: str
    content: str

class CommentLike(BaseModel):
    """点赞请求模型"""
    commentId: str
    liked: bool

class QuizOption(BaseModel):
    """问题选项模型"""
    label: str
    text: str
    isCorrect: bool

class Quiz(BaseModel):
    """互动问题模型"""
    id: str
    question: str
    options: List[QuizOption]

class QuizAnswer(BaseModel):
    """用户答案模型"""
    quizId: str
    selectedOption: str
    userName: Optional[str] = None
    userId: Optional[str] = None

class QuizResult(BaseModel):
    """答题结果模型"""
    isCorrect: bool
    correctAnswer: str
    message: str

# ==================== 内存数据存储 ====================
# 生产环境应该使用数据库

comments_db: List[Comment] = []

quizzes_db = {
    "quiz_1": Quiz(
        id="quiz_1",
        question="在小房间录音时，使用较长的混响时间会产生什么效果？",
        options=[
            QuizOption(label="A", text="让声音更干净清晰", isCorrect=False),
            QuizOption(label="B", text="声音会显得浑浊模糊", isCorrect=True),
            QuizOption(label="C", text="增强低频表现", isCorrect=False),
            QuizOption(label="D", text="提高音量响度", isCorrect=False),
        ]
    )
}

# 用户答题记录：{userId: {quizId: [answer_records]}}
user_quiz_records = {}

# 用户积分统计：{userName: {correct: int, wrong: int, score: int}}
user_scores = {}

# 问题统计：{quizId: {correct: int, wrong: int}}
quiz_stats = {}

# ==================== 工具函数 ====================

def format_time() -> str:
    """格式化当前时间为 HH:MM"""
    now = datetime.now()
    return now.strftime("%H:%M")

# ==================== 评论相关 API ====================

@app.post("/api/comments", response_model=Comment)
async def create_comment(comment_data: CommentCreate):
    """创建新评论"""
    comment = Comment(
        userName=comment_data.userName,
        content=comment_data.content,
        time=format_time()
    )
    comments_db.insert(0, comment)  # 新评论插入到最前面
    return comment

@app.get("/api/comments", response_model=List[Comment])
async def get_comments():
    """获取所有评论"""
    return comments_db

@app.post("/api/comments/like")
async def toggle_like(like_data: CommentLike):
    """切换评论点赞状态"""
    comment = next((c for c in comments_db if c.id == like_data.commentId), None)

    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    if like_data.liked:
        comment.likes += 1
        comment.liked = True
    else:
        comment.likes = max(0, comment.likes - 1)
        comment.liked = False

    return {"success": True, "likes": comment.likes}

@app.delete("/api/comments/{comment_id}")
async def delete_comment(comment_id: str):
    """删除评论（可选功能）"""
    global comments_db
    comments_db = [c for c in comments_db if c.id != comment_id]
    return {"success": True}

# ==================== 互动问题相关 API ====================

@app.get("/api/quizzes/{quiz_id}", response_model=Quiz)
async def get_quiz(quiz_id: str):
    """获取问题详情"""
    quiz = quizzes_db.get(quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="问题不存在")
    return quiz

@app.get("/api/quizzes", response_model=List[Quiz])
async def get_all_quizzes():
    """获取所有问题"""
    return list(quizzes_db.values())

@app.post("/api/quizzes/answer", response_model=QuizResult)
async def submit_answer(answer: QuizAnswer):
    """提交答案并返回结果"""
    quiz = quizzes_db.get(answer.quizId)

    if not quiz:
        raise HTTPException(status_code=404, detail="问题不存在")

    # 查找正确答案
    correct_option = next((opt for opt in quiz.options if opt.isCorrect), None)
    selected_option = next((opt for opt in quiz.options if opt.label == answer.selectedOption), None)

    if not correct_option or not selected_option:
        raise HTTPException(status_code=400, detail="无效的选项")

    is_correct = selected_option.isCorrect

    # 记录问题统计
    if answer.quizId not in quiz_stats:
        quiz_stats[answer.quizId] = {"correct": 0, "wrong": 0}

    if is_correct:
        quiz_stats[answer.quizId]["correct"] += 1
        message = "回答正确！"
    else:
        quiz_stats[answer.quizId]["wrong"] += 1
        message = "回答错误，重新试试吧"

    # 记录用户答题记录
    if answer.userName and answer.userId:
        # 初始化用户积分
        if answer.userName not in user_scores:
            user_scores[answer.userName] = {
                "correct": 0,
                "wrong": 0,
                "score": 0,
                "userId": answer.userId
            }

        # 更新用户积分
        if is_correct:
            user_scores[answer.userName]["correct"] += 1
            user_scores[answer.userName]["score"] += 10  # 正确+10分
        else:
            user_scores[answer.userName]["wrong"] += 1

        # 记录详细答题记录
        if answer.userId not in user_quiz_records:
            user_quiz_records[answer.userId] = {}

        if answer.quizId not in user_quiz_records[answer.userId]:
            user_quiz_records[answer.userId][answer.quizId] = []

        user_quiz_records[answer.userId][answer.quizId].append({
            "userName": answer.userName,
            "selectedOption": answer.selectedOption,
            "isCorrect": is_correct,
            "time": format_time(),
            "timestamp": datetime.now().isoformat()
        })

    return QuizResult(
        isCorrect=is_correct,
        correctAnswer=correct_option.label,
        message=message
    )

@app.get("/api/quizzes/{quiz_id}/stats")
async def get_quiz_stats(quiz_id: str):
    """获取问题答题统计"""
    stats = quiz_stats.get(quiz_id, {"correct": 0, "wrong": 0})
    total = stats["correct"] + stats["wrong"]
    accuracy = (stats["correct"] / total * 100) if total > 0 else 0

    return {
        **stats,
        "total": total,
        "accuracy": round(accuracy, 2)
    }

# ==================== 数据统计 API ====================

@app.get("/api/stats/users")
async def get_user_stats():
    """获取所有用户积分排行"""
    # 按积分排序
    sorted_users = sorted(
        user_scores.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    result = []
    for rank, (userName, stats) in enumerate(sorted_users, 1):
        result.append({
            "rank": rank,
            "userName": userName,
            "score": stats["score"],
            "correct": stats["correct"],
            "wrong": stats["wrong"],
            "total": stats["correct"] + stats["wrong"],
            "accuracy": round(stats["correct"] / (stats["correct"] + stats["wrong"]) * 100, 2)
                if (stats["correct"] + stats["wrong"]) > 0 else 0
        })

    return result

@app.get("/api/stats/overview")
async def get_overview_stats():
    """获取总体数据统计"""
    total_users = len(user_scores)
    total_comments = len(comments_db)

    # 计算总答题数
    total_answers = sum(stats["correct"] + stats["wrong"] for stats in quiz_stats.values())
    total_correct = sum(stats["correct"] for stats in quiz_stats.values())

    return {
        "totalUsers": total_users,
        "totalComments": total_comments,
        "totalAnswers": total_answers,
        "totalCorrect": total_correct,
        "overallAccuracy": round(total_correct / total_answers * 100, 2) if total_answers > 0 else 0
    }

@app.get("/api/stats/comments")
async def get_comment_stats():
    """获取评论统计"""
    # 统计每个用户的评论数
    user_comment_count = {}
    for comment in comments_db:
        userName = comment.userName
        user_comment_count[userName] = user_comment_count.get(userName, 0) + 1

    # 按评论数排序
    sorted_comments = sorted(
        user_comment_count.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [
        {"userName": userName, "commentCount": count}
        for userName, count in sorted_comments
    ]

@app.get("/api/stats/quiz-records")
async def get_all_quiz_records():
    """获取所有答题记录"""
    all_records = []

    for userId, quizzes in user_quiz_records.items():
        for quizId, records in quizzes.items():
            for record in records:
                all_records.append({
                    "userName": record["userName"],
                    "quizId": quizId,
                    "selectedOption": record["selectedOption"],
                    "isCorrect": record["isCorrect"],
                    "time": record["time"],
                    "timestamp": record["timestamp"]
                })

    # 按时间倒序排列
    all_records.sort(key=lambda x: x["timestamp"], reverse=True)

    return all_records

# ==================== Excel导出功能 ====================

def export_quiz_records_to_excel():
    """导出答题记录到Excel文件"""
    # 确保答题情况目录存在（云端使用临时目录）
    export_dir = os.path.join(os.getcwd(), "答题情况")
    os.makedirs(export_dir, exist_ok=True)

    # 创建工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "答题记录"

    # 设置列宽
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 18

    # 定义样式
    header_font = Font(name='微软雅黑', size=12, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')

    cell_font = Font(name='微软雅黑', size=11)
    cell_alignment = Alignment(horizontal='center', vertical='center')

    border = Border(
        left=Side(style='thin', color='D0D0D0'),
        right=Side(style='thin', color='D0D0D0'),
        top=Side(style='thin', color='D0D0D0'),
        bottom=Side(style='thin', color='D0D0D0')
    )

    # 写入表头
    headers = ['序号', '用户名', '问题ID', '选择答案', '答题结果', '答题时间']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border

    # 获取所有答题记录
    all_records = []
    for userId, quizzes in user_quiz_records.items():
        for quizId, records in quizzes.items():
            for record in records:
                all_records.append({
                    "userName": record["userName"],
                    "quizId": quizId,
                    "selectedOption": record["selectedOption"],
                    "isCorrect": record["isCorrect"],
                    "time": record["time"],
                    "timestamp": record["timestamp"]
                })

    # 按时间倒序排列
    all_records.sort(key=lambda x: x["timestamp"], reverse=True)

    # 写入数据
    for idx, record in enumerate(all_records, 2):
        # 序号
        cell = ws.cell(row=idx, column=1, value=idx-1)
        cell.font = cell_font
        cell.alignment = cell_alignment
        cell.border = border

        # 用户名
        cell = ws.cell(row=idx, column=2, value=record["userName"])
        cell.font = Font(name='微软雅黑', size=11, bold=True)
        cell.alignment = cell_alignment
        cell.border = border

        # 问题ID
        cell = ws.cell(row=idx, column=3, value=record["quizId"])
        cell.font = cell_font
        cell.alignment = cell_alignment
        cell.border = border

        # 选择答案
        cell = ws.cell(row=idx, column=4, value=record["selectedOption"])
        cell.font = cell_font
        cell.alignment = cell_alignment
        cell.border = border

        # 答题结果
        result_text = "✓ 正确" if record["isCorrect"] else "✗ 错误"
        cell = ws.cell(row=idx, column=5, value=result_text)
        cell.font = Font(name='微软雅黑', size=11, bold=True,
                        color='008000' if record["isCorrect"] else 'FF0000')
        cell.alignment = cell_alignment
        cell.border = border

        # 根据结果设置背景色
        if record["isCorrect"]:
            cell.fill = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
        else:
            cell.fill = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')

        # 答题时间
        cell = ws.cell(row=idx, column=6, value=record["time"])
        cell.font = cell_font
        cell.alignment = cell_alignment
        cell.border = border

    # 生成文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"答题记录_{timestamp}.xlsx"
    filepath = os.path.join(export_dir, filename)

    # 保存文件
    wb.save(filepath)

    return filepath

@app.get("/api/export/quiz-records")
async def export_quiz_records():
    """导出答题记录为Excel文件"""
    try:
        filepath = export_quiz_records_to_excel()
        filename = os.path.basename(filepath)

        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

@app.post("/api/export/auto-save")
async def auto_save_quiz_records():
    """自动保存答题记录到Excel（每次答题后调用）"""
    try:
        if len(user_quiz_records) == 0:
            return {"success": False, "message": "暂无答题记录"}

        filepath = export_quiz_records_to_excel()
        return {
            "success": True,
            "message": "答题记录已保存",
            "filepath": filepath
        }
    except Exception as e:
        return {"success": False, "message": f"保存失败: {str(e)}"}

# ==================== 管理页面 ====================

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """管理后台页面"""
    try:
        with open("admin.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return HTMLResponse(content="<h1>管理页面未找到</h1><p>请确保 admin.html 文件存在于后端目录</p>", status_code=404)

# ==================== 健康检查 ====================

@app.get("/")
async def root():
    """根路径，返回前端页面"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>前端页面未找到</h1><p>请确保 index.html 文件存在于后端目录</p>", status_code=404)

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

# ==================== 启动说明 ====================
# 运行命令: uvicorn main:app --reload --port 8000
# API 文档: http://localhost:8000/docs
