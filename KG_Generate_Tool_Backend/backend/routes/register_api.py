# from flask import Blueprint, request, jsonify
# from extensions import mail, r
# from flask_mail import Message
# import random
# from datetime import datetime
# from database import get_client
# import bcrypt
#
# register_bp = Blueprint('register', __name__)
#
#
# @register_bp.route('/public/send_code', methods=['POST'])
# def send_code():
#     data = request.get_json()
#     email = data.get('email')
#     if not email:
#         return jsonify({'status': 400, 'msg': '邮箱不能为空'})
#     if isinstance(email, dict):
#         email = list(email.values())[0]
#
#     # 生成 6 位验证码
#     code = ''.join(random.choices('0123456789', k=6))
#     r.setex(f'verify:{email}', 300, code)
#
#     try:
#         msg = Message(
#             subject='【图谱平台】邮箱验证码',
#             recipients=[email],
#             body=f'您的验证码是：{code}，5分钟内有效。'
#         )
#         mail.send(msg)
#         return jsonify({'status': 200, 'msg': '验证码发送成功'})
#     except Exception as e:
#         print(f'邮件发送失败: {e}')
#         return jsonify({'status': 500, 'msg': '发送失败，请稍后重试'})
#
#
# @register_bp.route('/public/register', methods=['POST'])
# def register():
#     data = request.get_json()
#     print(data)
#     name = data.get('name')
#     password = data.get('password')
#     email = data.get('email')
#     emailCode = data.get('emailCode')
#
#     # 验证邮箱验证码
#     saved_code = r.get(f'verify:{email}')
#     if not saved_code or saved_code != emailCode:
#         return jsonify({'status': 400, 'msg': '邮箱验证码错误或已过期'}), 400
#
#     try:
#         conn = get_client()
#         cursor = conn.cursor()
#
#         # 计算新 id
#         cursor.execute("SELECT COUNT(*) AS cnt FROM user_data")
#         count = cursor.fetchone()['cnt']
#         new_id = count + 1
#
#         # 加密密码
#         hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
#
#         # 时间格式
#         create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#
#         # 插入用户数据
#         insert_sql = """
#         INSERT INTO user_data (id, user_name, password, email, create_time)
#         VALUES (%s, %s, %s, %s, %s)
#         """
#         cursor.execute(insert_sql, (new_id, name, hashed_password, email, create_time))
#         conn.commit()
#
#         cursor.close()
#         conn.close()
#
#         # 删除验证码
#         r.delete(f'verify:{email}')
#
#         return jsonify({'status': 200, 'msg': '注册成功'})
#
#     except Exception as e:
#         print(f"注册失败: {e}")
#         if conn:
#             conn.rollback()
#             cursor.close()
#             conn.close()
#         return jsonify({'status': 500, 'msg': '注册失败，请稍后重试'}), 500

from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_client
import bcrypt

register_bp = Blueprint('register', __name__)


@register_bp.route('/public/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    print(data)
    name = (data.get('name') or '').strip()
    password = (data.get('password') or '').strip()
    email = (data.get('email') or '').strip()
    # emailCode = data.get('emailCode')  # 注释掉但保留，方便后续可能恢复

    if not name or not password:
        return jsonify({'status': 400, 'msg': '用户名和密码不能为空'}), 400
    if not email:
        return jsonify({'status': 400, 'msg': '邮箱不能为空'}), 400

    # 移除邮箱验证码验证
    # saved_code = r.get(f'verify:{email}')
    # if not saved_code or saved_code != emailCode:
    #     return jsonify({'status': 400, 'msg': '邮箱验证码错误或已过期'}), 400

    conn = None
    cursor = None
    try:
        conn = get_client()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM user_data WHERE user_name = %s", (name,))
        if cursor.fetchone():
            return jsonify({'status': 400, 'msg': '用户名已存在'}), 400

        cursor.execute("SELECT id FROM user_data WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'status': 400, 'msg': '邮箱已被使用'}), 400

        # 必须用 MAX(id)+1：COUNT(*)+1 在删除用户后会与已有 id 冲突，产生重复主键
        cursor.execute("SELECT MAX(id) AS max_id FROM user_data")
        row = cursor.fetchone()
        new_id = (row['max_id'] or 0) + 1

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        insert_sql = """
        INSERT INTO user_data (id, user_name, password, email, create_time)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_sql, (new_id, name, hashed_password, email, create_time))
        conn.commit()

        return jsonify({'status': 200, 'msg': '注册成功'})

    except Exception as e:
        print(f"注册失败: {e}")
        if conn:
            conn.rollback()
        return jsonify({'status': 500, 'msg': '注册失败，请稍后重试'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
