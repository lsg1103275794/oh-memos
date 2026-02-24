#!/usr/bin/env node
/**
 * MemOS Hook: UserPromptSubmit - Smart Intent Detection (Cross-platform Node.js)
 *
 * Analyzes user prompts and suggests relevant memory actions:
 * - Detects questions about past work → suggests memos_search
 * - Detects error reports → suggests searching ERROR_PATTERN
 * - Detects decision discussions → reminds to save as DECISION
 * - Detects completion signals → reminds to save MILESTONE
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
        continue: true,
        suppressOutput: false,
        message: `Memory hints:\n${suggestions}`
      }));
    } else {
      console.log(JSON.stringify({
        continue: true,
        suppressOutput: true
      }));
    }
  } catch (e) {
    console.log(JSON.stringify({
      continue: true,
      suppressOutput: true
    }));
  }
});

function detectIntents(prompt) {
  const intents = [];

  // History/Past Work Queries
  const historyPatterns = [
    /之前|上次|以前|earlier|previously|last time|remember when/,
    /怎么做的|怎么弄的|怎么解决的|how did (we|i|you)/,
    /有没有.*过|did (we|i|you).*before/
  ];
  if (historyPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'history_query',
      suggestion: '→ memos_search(query="...") to find related past work'
    });
  }

  // Error/Bug Reports
  const errorPatterns = [
    /error|错误|报错|failed|失败/,
    /exception|异常|crash|崩溃/,
    /不工作|doesn'?t work|not working|无法|cannot/,
    /traceback|stack trace|堆栈/
  ];
  if (errorPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'error_report',
      suggestion: '→ memos_search(query="ERROR_PATTERN <error>") for past solutions'
    });
  }

  // Decision Making
  const decisionPatterns = [
    /应该(用|选|采用)|should (we|i) (use|choose)/,
    /哪个更好|which (is|one|option) better/,
    /决定|decide|选择|choose between/,
    /方案|approach|strategy|architecture/
  ];
  if (decisionPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'decision_making',
      suggestion: '→ After deciding: memos_save(..., memory_type="DECISION")'
    });
  }

  // Task Completion Signals
  const completionPatterns = [
    /完成了|做完了|搞定了|finished|completed|done with/,
    /实现了|implemented|added|created/,
    /修复了|fixed|resolved|solved/
  ];
  if (completionPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'task_completion',
      suggestion: '→ Save: MILESTONE (big feature) / BUGFIX (fix) / FEATURE (new)'
    });
  }

  // Dependency/Relationship Queries
  const relationPatterns = [
    /为什么.*失败|why.*fail/,
    /什么导致|what caused|原因是/,
    /依赖|depends on|dependency/
  ];
  if (relationPatterns.some(p => p.test(prompt))) {
    intents.push({
      type: 'relationship_query',
      suggestion: '→ memos_get_graph or memos_trace_path for causal chains'
    });
  }

  return intents.slice(0, 2);
}
