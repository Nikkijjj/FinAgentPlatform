# backend/routes/user_api.py
import bcrypt
from database import get_client
from flask import Blueprint, request, jsonify
from datetime import datetime

# 定义 Blueprint
user_bp = Blueprint('user', __name__)


# 密码加密函数
def hash_password(password: str) -> str:
    """使用bcrypt加密密码"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


# 获取所有用户（不分页）- 用于前端分页
@user_bp.route('/users/all', methods=['GET'])
def get_all_users():
    """获取所有用户（不分页）"""
    try:
        search = request.args.get('search', '')

        client = get_client()
        with client.cursor() as cursor:
            # 构建查询条件
            where_clause = ""
            params = []

            if search:
                where_clause = "WHERE user_name LIKE %s OR email LIKE %s"
                search_pattern = f"%{search}%"
                params = [search_pattern, search_pattern]

            # 查询所有数据（不返回密码字段）
            sql = f"""
            SELECT id, user_name, email, create_time
            FROM user_data 
            {where_clause}
            ORDER BY id DESC
            """

            cursor.execute(sql, params)
            users = cursor.fetchall()

            # 格式化返回数据
            formatted_users = []
            for user in users:
                # 处理 create_time：如果已经是字符串，直接使用；如果是 datetime 对象，则格式化
                create_time = user['create_time']
                if create_time and hasattr(create_time, 'strftime'):
                    create_time = create_time.strftime('%Y-%m-%d %H:%M:%S')

                formatted_users.append({
                    'id': user['id'],
                    'user_name': user['user_name'],
                    'email': user['email'],
                    'create_time': create_time
                })

        response = jsonify({
            'status': 200,
            'message': 'success',
            'data': {
                'list': formatted_users,
                'total': len(formatted_users)
            }
        })

        # 添加禁用缓存的响应头
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    except Exception as e:
        print(f"[获取所有用户错误] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 500, 'message': f'服务器内部错误: {str(e)}'}), 500


# 原有的获取用户列表接口（保留，但前端不再使用）
@user_bp.route('/users', methods=['GET'])
def get_users():
    """获取用户列表（支持分页和搜索）- 保留向后兼容"""
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 10))
        search = request.args.get('search', '')

        # 计算偏移量
        offset = (page - 1) * page_size

        client = get_client()
        with client.cursor() as cursor:
            # 构建查询条件
            where_clause = ""
            params = []

            if search:
                where_clause = "WHERE user_name LIKE %s OR email LIKE %s"
                search_pattern = f"%{search}%"
                params = [search_pattern, search_pattern]

            # 查询总记录数
            count_sql = f"SELECT COUNT(*) as total FROM user_data {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']

            # 查询分页数据
            sql = f"""
            SELECT id, user_name, email, create_time
            FROM user_data 
            {where_clause}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """

            page_params = params + [page_size, offset]
            cursor.execute(sql, page_params)
            users = cursor.fetchall()

            # 格式化返回数据
            formatted_users = []
            for user in users:
                create_time = user['create_time']
                if create_time and hasattr(create_time, 'strftime'):
                    create_time = create_time.strftime('%Y-%m-%d %H:%M:%S')

                formatted_users.append({
                    'id': user['id'],
                    'user_name': user['user_name'],
                    'email': user['email'],
                    'create_time': create_time
                })

        response = jsonify({
            'status': 200,
            'message': 'success',
            'data': {
                'list': formatted_users,
                'total': total,
                'page': page,
                'pageSize': page_size
            }
        })

        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    except Exception as e:
        print(f"[获取用户列表错误] {str(e)}")
        return jsonify({'status': 500, 'message': '服务器内部错误'}), 500


# 获取单个用户信息
@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """根据ID获取用户信息"""
    try:
        client = get_client()
        with client.cursor() as cursor:
            sql = """
            SELECT id, user_name, email, create_time
            FROM user_data 
            WHERE id = %s
            """
            cursor.execute(sql, (user_id,))
            user = cursor.fetchone()

        if not user:
            return jsonify({'status': 404, 'message': '用户不存在'}), 404

        create_time = user['create_time']
        if create_time and hasattr(create_time, 'strftime'):
            create_time = create_time.strftime('%Y-%m-%d %H:%M:%S')

        formatted_user = {
            'id': user['id'],
            'user_name': user['user_name'],
            'email': user['email'],
            'create_time': create_time
        }

        response = jsonify({
            'status': 200,
            'message': 'success',
            'data': formatted_user
        })

        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    except Exception as e:
        print(f"[获取用户信息错误] {str(e)}")
        return jsonify({'status': 500, 'message': '服务器内部错误'}), 500


# 创建新用户
@user_bp.route('/users', methods=['POST'])
def create_user():
    """创建新用户"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 400, 'message': '请求数据必须为JSON格式'}), 400

        # 验证必填字段
        required_fields = ['username', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'status': 400, 'message': f'缺少必要参数: {field}'}), 400

        username = data['username'].strip()
        password = data['password'].strip()
        email = data.get('email', '').strip()

        client = get_client()
        with client.cursor() as cursor:
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM user_data WHERE user_name = %s", (username,))
            if cursor.fetchone():
                return jsonify({'status': 400, 'message': '用户名已存在'}), 400

            # 检查邮箱是否已存在（如果提供了邮箱）
            if email:
                cursor.execute("SELECT id FROM user_data WHERE email = %s", (email,))
                if cursor.fetchone():
                    return jsonify({'status': 400, 'message': '邮箱已被使用'}), 400

            # 加密密码
            hashed_password = hash_password(password)

            # 获取当前最大ID
            cursor.execute("SELECT MAX(id) as max_id FROM user_data")
            result = cursor.fetchone()
            new_id = (result['max_id'] or 0) + 1

            # 插入新用户
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            sql = """
            INSERT INTO user_data (id, user_name, password, email, create_time)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (new_id, username, hashed_password, email, now))
            client.commit()

        return jsonify({
            'status': 201,
            'message': '用户创建成功',
            'data': {
                'id': new_id,
                'username': username,
                'email': email,
                'create_time': now
            }
        }), 201

    except Exception as e:
        print(f"[创建用户错误] {str(e)}")
        return jsonify({'status': 500, 'message': '服务器内部错误'}), 500


# 更新用户信息
@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """更新用户信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 400, 'message': '请求数据必须为JSON格式'}), 400

        client = get_client()
        with client.cursor() as cursor:
            # 检查用户是否存在
            cursor.execute("SELECT id FROM user_data WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return jsonify({'status': 404, 'message': '用户不存在'}), 404

            # 构建更新字段
            update_fields = []
            params = []

            # 可更新的字段
            if 'email' in data:
                email = data['email'].strip()
                # 检查邮箱是否已被其他用户使用
                cursor.execute("SELECT id FROM user_data WHERE email = %s AND id != %s", (email, user_id))
                if cursor.fetchone():
                    return jsonify({'status': 400, 'message': '邮箱已被使用'}), 400
                update_fields.append("email = %s")
                params.append(email)

            # 如果要更新密码
            if 'password' in data and data['password']:
                hashed_password = hash_password(data['password'].strip())
                update_fields.append("password = %s")
                params.append(hashed_password)

            if 'username' in data:
                username = data['username'].strip()
                # 检查用户名是否已被其他用户使用
                cursor.execute("SELECT id FROM user_data WHERE user_name = %s AND id != %s", (username, user_id))
                if cursor.fetchone():
                    return jsonify({'status': 400, 'message': '用户名已存在'}), 400
                update_fields.append("user_name = %s")
                params.append(username)

            if not update_fields:
                return jsonify({'status': 400, 'message': '没有要更新的字段'}), 400

            # 添加用户ID
            params.append(user_id)

            # 执行更新
            sql = f"UPDATE user_data SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(sql, params)
            client.commit()

        return jsonify({
            'status': 200,
            'message': '用户更新成功'
        })

    except Exception as e:
        print(f"[更新用户错误] {str(e)}")
        return jsonify({'status': 500, 'message': '服务器内部错误'}), 500


# 删除用户
@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """删除用户"""
    try:
        client = get_client()
        with client.cursor() as cursor:
            # 检查用户是否存在
            cursor.execute("SELECT id FROM user_data WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return jsonify({'status': 404, 'message': '用户不存在'}), 404

            # 删除用户
            cursor.execute("DELETE FROM user_data WHERE id = %s", (user_id,))
            client.commit()

        return jsonify({
            'status': 200,
            'message': '用户删除成功'
        })

    except Exception as e:
        print(f"[删除用户错误] {str(e)}")
        return jsonify({'status': 500, 'message': '服务器内部错误'}), 500


# 批量删除用户
@user_bp.route('/users/batch', methods=['DELETE'])
def batch_delete_users():
    """批量删除用户"""
    try:
        data = request.get_json()
        if not data or 'user_ids' not in data:
            return jsonify({'status': 400, 'message': '请提供要删除的用户ID列表'}), 400

        user_ids = data['user_ids']
        if not isinstance(user_ids, list) or len(user_ids) == 0:
            return jsonify({'status': 400, 'message': '用户ID列表不能为空'}), 400

        # 转换为元组用于SQL IN查询
        placeholders = ','.join(['%s'] * len(user_ids))

        client = get_client()
        with client.cursor() as cursor:
            # 批量删除
            sql = f"DELETE FROM user_data WHERE id IN ({placeholders})"
            cursor.execute(sql, user_ids)
            client.commit()

            deleted_count = cursor.rowcount

        return jsonify({
            'status': 200,
            'message': f'成功删除{deleted_count}个用户',
            'data': {
                'deleted_count': deleted_count
            }
        })

    except Exception as e:
        print(f"[批量删除用户错误] {str(e)}")
        return jsonify({'status': 500, 'message': '服务器内部错误'}), 500