# 将对联文本加载到向量数据库中。

import os
import redis
from langchain_community.embeddings import DashScopeEmbeddings


embedding_model = DashScopeEmbeddings(
    dashscope_api_key="sk-0e1e78cdb7034f8babefc27516eaedf2",
    model="text-embedding-v1"
    )



# 3、保存向量数据库
redis_url = "redis://localhost:6379"

redis_client = redis.from_url(redis_url)
# print(redis_client.ping())  # 测试连接 返回True表示连接成功

from langchain_redis import RedisConfig, RedisVectorStore
config = RedisConfig(
    index_name="couplet",
    redis_url=redis_url
)

vector_store = RedisVectorStore(embedding_model, config=config)

lines = []
with open("../datasets/train.csv", "r", encoding="utf-8") as file:
    for line in file:
        print(line)
        lines.append(line)

vector_store.add_texts(lines)