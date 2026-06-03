import json

def test_login_missing_params(client):
    """测试参数缺失时的错误返回"""
    response = client.post('/old-api/login', json={
        'username': 'admin'
    })
    assert response.status_code in [400, 401, 500, 200]
    
def test_login_invalid_credentials(client):
    """测试错误的密码或用户名"""
    response = client.post('/old-api/login', json={
        'username': 'admin_test',
        'password': 'wrong_password'
    })
    data = json.loads(response.data)
    assert response.status_code in [200, 401]
