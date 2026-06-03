import os
from dotenv import load_dotenv

# Langfuse tracing
from langfuse import Langfuse
from flask import Flask, jsonify
from flask_cors import CORS
from routes.login_api import login_bp
from routes.textPreprocess_api import textPreprocess_bp  # 导入 Blueprint
from routes.projectManage_api import projectManage_bp
from routes.dashboard_api import dashboard_bp
from routes.extractSample_bp import extractSample_bp, logger
from routes.askAI_api import askAI_bp
from routes.utils_api import utils_bp
from config import Config
# from extensions import mail
from routes.register_api import register_bp
from routes.llmGenKG_api import llmGenKG_bp
from routes.user_api import user_bp
from routes.evolution_api import evolution_bp  # 新增：图谱动态演进 API
from routes.message_api import message_bp

load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)
# mail.init_app(app)
CORS(app, supports_credentials=True, origins=["http://localhost:8000"])

# Langfuse client setup (global)
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL")
langfuse = None
if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
    langfuse = Langfuse(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_BASE_URL,
    )
else:
    print("[langfuse] LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY 未配置，已跳过 tracing 初始化")
# 注册 API
app.register_blueprint(login_bp, url_prefix='/old-api')
app.register_blueprint(register_bp, url_prefix='/old-api')
app.register_blueprint(user_bp, url_prefix='/old-api')
app.register_blueprint(utils_bp, url_prefix='/old-api')
app.register_blueprint(textPreprocess_bp, url_prefix='/api')
app.register_blueprint(projectManage_bp, url_prefix='/old-api')
app.register_blueprint(askAI_bp, url_prefix='/old-api')
app.register_blueprint(dashboard_bp)
app.register_blueprint(message_bp)
app.register_blueprint(extractSample_bp, url_prefix='/old-api')
app.register_blueprint(llmGenKG_bp, url_prefix='/old-api/llmGenKG')
app.register_blueprint(evolution_bp, url_prefix='/old-api/evolution')  # 注册演进 API


def start_event_data_scheduler():
    """每日定时同步 event_data 及 后台图谱动态演进检测。"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from event_data_sync import run_sync
        from auto_evolution_task import run_auto_evolution_job  # 导入演进任务

        scheduler = BackgroundScheduler()
        # 每天凌晨 2 点执行一次数据同步
        scheduler.add_job(run_sync, "cron", hour=2, minute=0)
        
        # 每隔 15 秒检查一次是否有项目需要动态图谱演进（用于演示实时性）
        scheduler.add_job(run_auto_evolution_job, "interval", seconds=15)
        
        scheduler.start()
        print("[Scheduler] 后台调度器已启动（包含 event_data 同步及 动态图谱演进）")
    except Exception as e:
        print(f"[Scheduler] 定时任务未启动: {e}")


if __name__ == '__main__':
    # 应用启动时尝试做一次 MongoDB 增量同步（不依赖定时器、与是否 debug 无关）
    try:
        from event_data_sync import sync_to_mongo
        print("[event_data] 应用启动，触发一次 MongoDB 增量同步（如有新增数据将写入）")
        sync_to_mongo()
    except Exception as inner_e:
        print(f"[event_data] 启动时 MongoDB 增量同步失败: {inner_e}")

    # 在真正运行应用的进程中启动每日同步定时任务（debug 重载时仅子进程启动）
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        start_event_data_scheduler()

    # Attach langfuse client to app for global access
    app.langfuse = langfuse

    app.run(host='0.0.0.0', port=5000, debug=False)  # 运行 Flask 服务器
