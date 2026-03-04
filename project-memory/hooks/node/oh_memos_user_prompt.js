#!/usr/bin/env node
/**
 * MemOS Hook: UserPromptSubmit - Smart Intent Detection (Cross-platform Node.js)
 *
 * Analyzes user prompts and suggests relevant memory actions:
 * - Detects questions about past work → suggests memos_search
 * - Detects error reports → suggests searching ERROR_PATTERN
 * - Detects decision discussions → reminds to save as DECISION
 * - Detects completion signals → reminds to save MILESTONE
 *
 * Response format: { systemMessage: "..." } or {} (standard Claude Code hook format)
 */

let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const prompt = (data.prompt || '').toLowerCase();

    const intents = detectIntents(prompt);

    if (intents.length > 0) {
      const suggestions = intents.map(i => i.suggestion).join('\n');
      console.log(JSON.stringify({
        systemMessage: `Memory hints:\n${suggestions}`
      }));
    } else {
      console.log(JSON.stringify({}));
    }
  } catch (e) {
    console.log(JSON.stringify({}));
  }
});

/**
 * Detect user intents from prompt text
 * @param {string} prompt - User prompt in lowercase
 * @returns {Array} Array of detected intents with suggestions
 */
function detectIntents(prompt) {
  const intents = [];

  // === 1. History/Past Work Queries ===
  const historyPatterns = [
    /之前|上次|以前|earlier|previously|last time|remember when/,
    /怎么做的|怎么弄的|怎么解决的|how did (we|i|you)/,
    /有没有.*过|did (we|i|you).*before/,
    /什么时候.*的|when did (we|i|you)/
  ];
  if (historyPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'history_query',
      suggestion: '→ memos_search(query="...") to find related past work'
    });
  }

  // === 2. Error/Bug Reports ===
  const errorPatterns = [
    /error|错误|报错|failed|失败/,
    /exception|异常|crash|崩溃/,
    /不工作|doesn'?t work|not working|无法|cannot/,
    /bug|问题|issue|trouble/,
    /traceback|stack trace|堆栈/
  ];
  if (errorPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'error_report',
      suggestion: '→ memos_search(query="ERROR_PATTERN <error>") for past solutions'
    });
  }

  // === 3. Decision Making ===
  const decisionPatterns = [
    /应该(用|选|采用)|should (we|i) (use|choose)/,
    /哪个更好|which (is|one|option) better/,
    /决定|decide|选择|choose between/,
    /vs\.?|versus|还是|or should/,
    /方案|approach|strategy|architecture/
  ];
  if (decisionPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'decision_making',
      suggestion: '→ After deciding: memos_save(..., memory_type="DECISION")'
    });
  }

  // === 4. Task Completion Signals ===
  const completionPatterns = [
    /完成了|做完了|搞定了|finished|completed|done with/,
    /实现了|implemented|added|created/,
    /修复了|fixed|resolved|solved/,
    /已经.*好了|just.*finished/
  ];
  if (completionPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'task_completion',
      suggestion: '→ Save: MILESTONE (big feature) / BUGFIX (fix) / FEATURE (new)'
    });
  }

  // === 5. Dependency/Relationship Queries ===
  const relationPatterns = [
    /为什么.*失败|why.*fail/,
    /什么导致|what caused|原因是/,
    /依赖|depends on|dependency/,
    /关系|relationship|related to|连接/
  ];
  if (relationPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'relationship_query',
      suggestion: '→ memos_get_graph or memos_trace_path for causal chains'
    });
  }

  // === 6. Project Status Queries ===
  const statusPatterns = [
    /进度|progress|status|情况/,
    /做了什么|what have (we|i|you) done/,
    /总结|summary|overview|概述/,
    /还有什么|what's left|remaining|剩下/
  ];
  if (statusPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'status_query',
      suggestion: '→ memos_list or memos_get_stats for project overview'
    });
  }

  // === 7. Configuration/Setup Topics ===
  const configPatterns = [
    /配置|config|setup|设置/,
    /环境变量|env|environment/,
    /安装|install|部署|deploy/
  ];
  if (configPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'config_topic',
      suggestion: '→ After changes: memos_save(..., memory_type="CONFIG")'
    });
  }

  // Limit to top 2 most relevant suggestions to avoid noise
  return intents.slice(0, 2);
}
