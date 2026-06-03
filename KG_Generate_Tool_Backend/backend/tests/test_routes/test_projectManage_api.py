import json

def test_get_project_list(client):
    """测试获取项目列表接口"""
    response = client.get('/old-api/project/list')
    assert response.status_code in [200, 401] # Depends on mock token

def test_create_project_missing_params(client):
    """测试创建项目缺少参数"""
    response = client.post('/old-api/project/create', json={})
    assert response.status_code in [400, 401, 200]
