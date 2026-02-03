1.https://cloud.siliconflow.cn/i/eaey72Uc   # 硅基流动提供了16元的额度且部分向量模型和重排模型都是免费的 本软件包括作者使用的都是免费的向量和重排模型

2.# 智谱大模型开放平台 BigModel.cn上打造AI应用，智谱新一代旗舰模型GLM-4.7已上线， 在推理、代码、智能体综合能力达到开源模型 SOTA 水平，通过我的邀请链接注册即可获得 2000万Tokens 大礼包，期待和你一起在BigModel上畅享卓越模型能力；智谱同样提供了巨大的免费的API调用额度还有向量模型届时您如果需要LLM知识图谱构建时可以充分利用免费的LLM API调用 也支持ollama的本地LLM调用来处理知识图谱构建！
链接：https://www.bigmodel.cn/invite?icode=N7oEU%2Bnf%2FYMXf5Qubj7%2BWrC%2Fk7jQAKmT1mpEiZXXnFw%3D

3.假如您使用本地ollama 我们推荐您使用如下配置您只需要运行ollama pull dengcao/bge-m3:567m 然后在.env配置：

MOS_EMBEDDER_FALLBACK_ENABLED=true
MOS_EMBEDDER_FALLBACK_BACKEND=ollama
MOS_EMBEDDER_FALLBACK_MODEL=dengcao/bge-m3:567m
MOS_EMBEDDER_FALLBACK_API_BASE=http://localhost:11434
MOS_EMBEDDER_FALLBACK_MAX_RETRIES=3
MOS_EMBEDDER_FALLBACK_DIMENSION_STRATEGY=error



届时您只需填写您申请到的API key到根目录下的.env文件如下格式 您也可以复制如下到.env 如果您电脑配置丰富完全可以使用基于本地的ollama模型达到所有数据都在本地处理
# ============================================================================
# 嵌入模型 (Embedder)
# ============================================================================
EMBEDDING_DIMENSION=1024                            # 嵌入向量维度
MOS_EMBEDDER_BACKEND=universal_api                  # 后端类型 (ollama / universal_api)
MOS_EMBEDDER_PROVIDER=openai                        # API 提供商 (universal_api 时需要)
MOS_EMBEDDER_MODEL=BAAI/bge-m3                      # 模型名称
MOS_EMBEDDER_API_BASE=https://api.siliconflow.cn/v1 # API 地址
MOS_EMBEDDER_API_KEY=  # API 密钥

# ============================================================================
# 重排序模型 (Reranker)
# ============================================================================
MOS_RERANKER_BACKEND=http_bge                       # 后端类型 (http_bge / cosine_local / noop)
MOS_RERANKER_URL=https://api.siliconflow.cn/v1      # API 地址
MOS_RERANKER_MODEL=netease-youdao/bce-reranker-base_v1  # 模型名称
MOS_RERANKER_API_KEY= # API 密钥
MOS_RERANKER_HEADERS_EXTRA=                         # 额外请求头
MOS_RERANKER_STRATEGY=single_turn                   # 重排策略
