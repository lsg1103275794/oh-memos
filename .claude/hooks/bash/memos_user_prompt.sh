#!/bin/bash
# MemOS Hook: UserPromptSubmit - Smart Intent Detection
#
# Analyzes user prompts and suggests relevant memory actions

# Read input from stdin
input=$(cat)

# Extract prompt (basic JSON parsing)
prompt=$(echo "$input" | grep -oP '"prompt"\s*:\s*"\K[^"]*' 2>/dev/null | tr '[:upper:]' '[:lower:]')

suggestions=""

# === 1. History/Past Work Queries ===
if echo "$prompt" | grep -qiE "之前|上次|以前|earlier|previously|last time|remember when|怎么做的|怎么弄的|怎么解决的|how did"; then
    suggestions="${suggestions}→ Consider: memos_search to find related past work\n"
fi

# === 2. Error/Bug Reports ===
if echo "$prompt" | grep -qiE "error|错误|报错|failed|失败|exception|异常|crash|崩溃|不工作|doesn't work|not working|无法|cannot|bug|traceback"; then
    suggestions="${suggestions}→ Consider: memos_search(query=\"ERROR_PATTERN ...\") for past solutions\n"
fi

# === 3. Decision Making ===
if echo "$prompt" | grep -qiE "应该用|应该选|应该采用|should we use|should i use|哪个更好|which is better|决定|decide|选择|choose between|vs|方案|approach|strategy|architecture"; then
    suggestions="${suggestions}→ After deciding: memos_save(..., memory_type=\"DECISION\")\n"
fi

# === 4. Task Completion Signals ===
if echo "$prompt" | grep -qiE "完成了|做完了|搞定了|finished|completed|done with|实现了|implemented|added|created|修复了|fixed|resolved|solved"; then
    suggestions="${suggestions}→ Consider saving: MILESTONE (big feature) / BUGFIX (fix) / FEATURE (new)\n"
fi

# === 5. Dependency/Relationship Queries ===
if echo "$prompt" | grep -qiE "为什么.*失败|why.*fail|什么导致|what caused|原因是|依赖|depends on|dependency|关系|relationship|related to"; then
    suggestions="${suggestions}→ Consider: memos_get_graph or memos_trace_path for causal chains\n"
fi

# === 6. Project Status Queries ===
if echo "$prompt" | grep -qiE "进度|progress|status|情况|做了什么|what have we done|总结|summary|overview|概述|还有什么|what's left|remaining|剩下"; then
    suggestions="${suggestions}→ Consider: memos_list or memos_get_stats for project overview\n"
fi

# === 7. Configuration/Setup Topics ===
if echo "$prompt" | grep -qiE "配置|config|setup|设置|环境变量|env|environment|安装|install|部署|deploy"; then
    suggestions="${suggestions}→ After changes: memos_save(..., memory_type=\"CONFIG\")\n"
fi

# Output result
if [ -n "$suggestions" ]; then
    # Limit to first 2 lines
    suggestions=$(echo -e "$suggestions" | head -n 2 | tr '\n' '\\n' | sed 's/\\n$//')
    echo "{\"continue\":true,\"suppressOutput\":false,\"message\":\"🧠 Memory hints:\\n${suggestions}\"}"
else
    echo '{"continue":true,"suppressOutput":true}'
fi
