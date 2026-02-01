# Progress: 关键词查询优化

## Session 2026-02-01

### 15:00 - 开始分析

**完成：**
- [x] 分析现有搜索架构
- [x] 理解 MCP Server 关键词处理逻辑
- [x] 识别 BM25 和向量搜索实现
- [x] 创建任务计划和发现文档

**关键发现：**

1. **现有架构已较完善**
   - 三路并行搜索：向量 + 图 + BM25
   - 关键词评分和重排序已实现
   - 中英文分词和停用词过滤已有

2. **优化空间**
   - 停用词列表较小（41个）
   - 未利用结构化字段权重（key, tags）
   - 无模糊匹配/拼写纠错
   - 无倒排索引加速

3. **关键文件**
   - `mcp-server/memos_mcp_server.py:804-880` - 关键词处理
   - `retrieve/bm25_util.py` - BM25 实现
   - `retrieve/recall.py` - 混合检索

---

### 15:30 - 实现增强功能

**完成：**
- [x] 创建 `keyword_enhancer.py` 模块
- [x] 扩展停用词库（800+ 英文 + 300+ 中文）
- [x] 实现 Levenshtein 模糊匹配
- [x] 实现结构化字段权重（key: 5.0, tags: 3.0, text: 2.5）
- [x] 实现智能 cube 检测（从项目路径推导）
- [x] 集成到 MCP Server

**新增文件：**
- `mcp-server/keyword_enhancer.py` - 关键词增强模块

**修改文件：**
- `mcp-server/memos_mcp_server.py` - 集成增强模块

**增强功能：**

1. **扩展停用词库**
   - 编程相关：function, class, method, return, etc.
   - 中文：综合百度、哈工大、四川大学停用词表

2. **模糊匹配**
   - Levenshtein 距离算法
   - 阈值：0.75 相似度
   - 自动容错拼写错误

3. **结构化字段权重**
   ```
   key 字段匹配: +5.0
   tags 匹配:    +3.0
   正文精确:     +2.5
   正文子串:     +1.5
   模糊匹配:     +1.0 * similarity
   ```

4. **智能 Cube 检测**
   - 从 CWD 推导项目名
   - 标准化：小写、替换特殊字符、添加 _cube 后缀
   - 示例：`/mnt/g/test/MemOS` → `memos_cube`

---

## 待处理

- [ ] 添加单元测试
- [ ] 性能基准测试
- [ ] 考虑添加同义词扩展
- [ ] 考虑添加倒排索引

---

## Test Results

**All tests passed (5/5):**

```
============================================================
Test: Stopwords Library
============================================================
Total stopwords: 1300
English stopwords: 816
Chinese stopwords: 484
  [OK] 'the', 'and', 'function', 'class' - stopwords
  [OK] '的', '是', 'import', 'return' - stopwords

============================================================
Test: Keyword Extraction
============================================================
  [OK] English stopwords filtered correctly
  [OK] Chinese continuous chars kept as token
  [OK] Mixed language handling

============================================================
Test: Fuzzy Matching
============================================================
  [OK] 'configration' -> 'configuration' (score: 0.92)
  [OK] 'databse' -> 'database' (score: 0.88)

============================================================
Test: Keyword Match Scoring
============================================================
  Score without metadata: 9.00
  Score with key match:   14.00 (+55%)
  Score with tag match:   15.00 (+67%)

============================================================
Test: Smart Cube Detection
============================================================
  [OK] /mnt/g/test/MemOS -> memos_cube
  [OK] C:\Projects\WebApp -> webapp_cube
  [OK] /home/user/my-project -> my_project_cube
```
