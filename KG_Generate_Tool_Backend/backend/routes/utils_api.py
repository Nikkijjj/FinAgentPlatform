# backend/routes/utils_api.py
import jwt
import logging
from flask import Blueprint, request, jsonify

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义 Blueprint
utils_bp = Blueprint('utils', __name__)

SECRET_KEY = 'your_secure_secret_key_here'
AVATAR_URL = 'https://s11.ax1x.com/2023/12/15/pihx4js.jpg'

def getUserName(token):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_name = payload.get('username')
    return user_name

# 获取token中用户信息接口
@utils_bp.route('/util/getUserInfo', methods=['GET'])
def get_user_info():
    # 从请求头获取 Authorization: Bearer <token>
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'msg': '缺少或格式错误的Token', 'code': 401}), 401

    token = auth_header.split(' ')[1]

    try:
        # 解析 token，获取 payload
        user_name = getUserName(token)
        if not user_name:
            return jsonify({'msg': 'Token中缺少用户名信息', 'code': 400}), 400

        return jsonify({
            'msg': '操作成功',
            'status': 200,
            'data': {
                'userName': user_name,
                'nickName': user_name,
                'avatar': AVATAR_URL
            }
        })

    except jwt.ExpiredSignatureError:
        return jsonify({'msg': 'Token已过期', 'code': 401})
    except jwt.InvalidTokenError:
        return jsonify({'msg': '无效的Token', 'code': 401})
    except Exception as e:
        print(f"[解析Token异常] {str(e)}")
        return jsonify({'msg': '服务器错误', 'code': 500})


@utils_bp.route('/event-data/sync-mongo', methods=['POST'])
def trigger_mongo_sync():
    """触发 MongoDB 全量数据同步"""
    try:
        # 从 event_data_sync 导入 MongoDB 同步函数
        from event_data_sync import sync_to_mongo

        # 执行同步
        count = sync_to_mongo()

        return jsonify({
            'msg': 'MongoDB 同步成功',
            'code': 200,
            'count': count,
            'database': 'mongodb'
        })
    except ImportError as e:
        logger.error(f"导入 MongoDB 同步模块失败: {e}")
        return jsonify({
            'msg': f'MongoDB 同步模块不存在: {str(e)}',
            'code': 500
        }), 500
    except Exception as e:
        logger.error(f"MongoDB 同步失败: {e}")
        return jsonify({
            'msg': f'MongoDB 同步失败: {str(e)}',
            'code': 500
        }), 500