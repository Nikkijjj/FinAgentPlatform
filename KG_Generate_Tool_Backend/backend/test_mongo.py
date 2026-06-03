from pymongo import MongoClient

# 连接 MongoDB（默认本地 27017 端口）
client = MongoClient('mongodb://localhost:27017/')

# 选择数据库（finkg1，如果不存在会自动创建）
db = client['finkg1']

# 选择集合（相当于 MySQL 的表）
collection = db['event_data']

# 插入一条测试数据
result = collection.insert_one({"test": "hello mongodb"})
print(f"插入成功，ID: {result.inserted_id}")

# 查询数据
doc = collection.find_one({"test": "hello mongodb"})
print(f"查询结果: {doc}")