# Hook Reference

> Complete reference for implementing skill trigger hooks

---

## Overview

Claude Code supports three hook types:

| Hook Type | When Triggered | Purpose |
|-----------|----------------|---------|
| PreToolUse | Before tool execution | Validation, parameter modification |
| PostToolUse | After tool execution | Auto-format, checks, learning |
| Stop | When session ends | Final verification, cleanup |

For skill triggering, we use:
- **UserPromptSubmit** (custom hook for user input analysis)
- **PostToolUse** (for learning from skill usage)

---

## Hook Locations

```
.claude/
├── hooks/
│   ├── bash/
│   │   ├── user-prompt-submit.sh
│   │   └── post-tool-use.sh
│   ├── powershell/
│   │   ├── UserPromptSubmit.ps1
│   │   └── PostToolUse.ps1
│   └── node/
│       └── user-prompt-submit.js
```

---

## UserPromptSubmit Hook

### Bash Implementation

**File:** `.claude/hooks/bash/user-prompt-submit.sh`

```bash
#!/bin/bash
################################################################################
# UserPromptSubmit Hook - Skill Recommendation System
#
# Triggered: Before processing user input
# Purpose: Recommend relevant skills based on user intent
################################################################################

set -e

# Configuration
CUBE_ID="${MEMOS_DEFAULT_CUBE:-dev_cube}"
CONFIG_FILE="${HOME}/.claude/config/skill-trigger-config.json"
CONFIDENCE_THRESHOLD=0.6
MAX_RECOMMENDATIONS=5

# Load configuration if exists
if [ -f "$CONFIG_FILE" ]; then
    CONFIDENCE_THRESHOLD=$(jq -r '.confidence_threshold // 0.6' "$CONFIG_FILE")
    MAX_RECOMMENDATIONS=$(jq -r '.max_recommendations // 5' "$CONFIG_FILE")
fi

# Get user input (passed as first argument)
USER_INPUT="$1"

# If input is empty, exit
if [ -z "$USER_INPUT" ]; then
    exit 0
fi

# Normalize input (lowercase, remove extra spaces)
QUERY=$(echo "$USER_INPUT" | tr '[:upper:]' '[:lower:]' | tr -s ' ')

# Get conversation history (last 5 turns)
# Note: This depends on Claude Code's hook API
CONVERSATION_HISTORY=$(cat "$CLAUDE_TEMP_DIR/conversation_history.json" 2>/dev/null || echo "[]")

# Build JSON payload for memory search
PAYLOAD=$(cat <<EOF
{
  "cube_id": "$CUBE_ID",
  "query": "$QUERY",
  "context": $CONVERSATION_HISTORY,
  "top_k": $MAX_RECOMMENDATIONS
}
EOF
)

# Call memory search (via MCP or direct API)
SEARCH_RESULT=$(curl -s -X POST \
  "http://localhost:18000/product/search" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  2>/dev/null || echo "{}")

# Parse results and filter by confidence
RECOMMENDATIONS=$(echo "$SEARCH_RESULT" | \
  jq -r --arg threshold "$CONFIDENCE_THRESHOLD" \
  '.items[] | select(.confidence > ($threshold | tonumber)) |
     "\(.skill_name): \(.description) (confidence: \(.confidence))"' \
  2>/dev/null || echo "")

# Display recommendations if found
if [ -n "$RECOMMENDATIONS" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 Recommended Skills:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Colorize output (green for high confidence, yellow for medium)
    while IFS= read -r line; do
        if echo "$line" | grep -q "confidence: [89]."; then
            echo -e "\033[32m$line\033[0m"  # Green
        else
            echo -e "\033[33m$line\033[0m"  # Yellow
        fi
    done <<< "$RECOMMENDATIONS"

    echo ""
    echo "Use /<skill-name> to invoke a skill"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

# Save this input for learning (if skill is used later)
echo "$USER_INPUT" > "$CLAUDE_TEMP_DIR/last_user_input.txt"

exit 0
```

### PowerShell Implementation

**File:** `.claude/hooks/powershell/UserPromptSubmit.ps1`

```powershell
################################################################################
# UserPromptSubmit Hook - Skill Recommendation System (PowerShell)
#
# Triggered: Before processing user input
# Purpose: Recommend relevant skills based on user intent
################################################################################

param(
    [Parameter(Mandatory=$true)]
    [string]$UserInput
)

# Configuration
$ConfigFile = Join-Path $env:USERPROFILE ".claude\config\skill-trigger-config.json"
$CubeId = $env:MEMOS_DEFAULT_CUBE ?? "dev_cube"
$ConfidenceThreshold = 0.6
$MaxRecommendations = 5

# Load configuration if exists
if (Test-Path $ConfigFile) {
    $Config = Get-Content $ConfigFile | ConvertFrom-Json
    $ConfidenceThreshold = $Config.confidence_threshold ?? 0.6
    $MaxRecommendations = $Config.max_recommendations ?? 5
}

# Exit if input is empty
if ([string]::IsNullOrWhiteSpace($UserInput)) {
    exit 0
}

# Normalize input
$Query = $UserInput.ToLower().Trim()

# Get conversation history
$HistoryFile = Join-Path $env:CLAUDE_TEMP_DIR "conversation_history.json"
$ConversationHistory = if (Test-Path $HistoryFile) {
    Get-Content $HistoryFile | ConvertFrom-Json
} else {
    @()
}

# Build payload
$Payload = @{
    cube_id = $CubeId
    query = $Query
    context = $ConversationHistory
    top_k = $MaxRecommendations
} | ConvertTo-Json -Depth 10

# Call memory search
try {
    $SearchResult = Invoke-RestMethod -Uri "http://localhost:18000/product/search" `
        -Method POST `
        -ContentType "application/json" `
        -Body $Payload
} catch {
    # API call failed, exit silently
    exit 0
}

# Filter recommendations by confidence
$Recommendations = $SearchResult.items | Where-Object {
    $_.confidence -gt $ConfidenceThreshold
}

# Display recommendations if found
if ($Recommendations.Count -gt 0) {
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host "💡 Recommended Skills:"
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    foreach ($Rec in $Recommendations) {
        if ($Rec.confidence -ge 0.8) {
            Write-Host "$($Rec.skill_name): $($Rec.description) (confidence: $($Rec.confidence))" `
                -ForegroundColor Green
        } else {
            Write-Host "$($Rec.skill_name): $($Rec.description) (confidence: $($Rec.confidence))" `
                -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "Use /<skill-name> to invoke a skill"
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Save input for learning
$LastInputFile = Join-Path $env:CLAUDE_TEMP_DIR "last_user_input.txt"
$UserInput | Out-File -FilePath $LastInputFile -Encoding utf8

exit 0
```

### Node.js Implementation

**File:** `.claude/hooks/node/user-prompt-submit.js`

```javascript
#!/usr/bin/env node
/**
 * UserPromptSubmit Hook - Skill Recommendation System (Node.js)
 *
 * Triggered: Before processing user input
 * Purpose: Recommend relevant skills based on user intent
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

// Configuration
const configPath = path.join(process.env.HOME, '.claude/config/skill-trigger-config.json');
const cubeId = process.env.MEMOS_DEFAULT_CUBE || 'dev_cube';
const tempDir = process.env.CLAUDE_TEMP_DIR || '/tmp';

let confidenceThreshold = 0.6;
let maxRecommendations = 5;

// Load configuration
if (fs.existsSync(configPath)) {
    try {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        confidenceThreshold = config.confidence_threshold || 0.6;
        maxRecommendations = config.max_recommendations || 5;
    } catch (err) {
        console.error('Error loading config:', err.message);
    }
}

// Get user input
const userInput = process.argv[2];

if (!userInput) {
    process.exit(0);
}

// Normalize input
const query = userInput.toLowerCase().trim();

// Get conversation history
let conversationHistory = [];
try {
    const historyPath = path.join(tempDir, 'conversation_history.json');
    if (fs.existsSync(historyPath)) {
        conversationHistory = JSON.parse(fs.readFileSync(historyPath, 'utf8'));
    }
} catch (err) {
    // Ignore history errors
}

// Build payload
const payload = JSON.stringify({
    cube_id: cubeId,
    query: query,
    context: conversationHistory,
    top_k: maxRecommendations
});

// Call memory search
const options = {
    hostname: 'localhost',
    port: 18000,
    path: '/product/search',
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
    }
};

const req = https.request(options, (res) => {
    let data = '';

    res.on('data', (chunk) => {
        data += chunk;
    });

    res.on('end', () => {
        try {
            const result = JSON.parse(data);

            // Filter recommendations
            const recommendations = (result.items || []).filter(
                item => item.confidence > confidenceThreshold
            );

            // Display recommendations
            if (recommendations.length > 0) {
                console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
                console.log('💡 Recommended Skills:');
                console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

                recommendations.forEach(rec => {
                    const confidence = rec.confidence.toFixed(2);
                    if (rec.confidence >= 0.8) {
                        console.log(`\x1b[32m${rec.skill_name}: ${rec.description} (confidence: ${confidence})\x1b[0m`);
                    } else {
                        console.log(`\x1b[33m${rec.skill_name}: ${rec.description} (confidence: ${confidence})\x1b[0m`);
                    }
                });

                console.log('');
                console.log('Use /<skill-name> to invoke a skill');
                console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            }
        } catch (err) {
            // Ignore parse errors
        }

        // Save input for learning
        try {
            fs.writeFileSync(path.join(tempDir, 'last_user_input.txt'), userInput);
        } catch (err) {
            // Ignore write errors
        }

        process.exit(0);
    });
});

req.on('error', (err) => {
    // API call failed, exit silently
    process.exit(0);
});

req.write(payload);
req.end();
```

---

## PostToolUse Hook (Learning System)

### Bash Implementation

**File:** `.claude/hooks/bash/post-tool-use.sh`

```bash
#!/bin/bash
################################################################################
# PostToolUse Hook - Skill Learning System
#
# Triggered: After tool execution
# Purpose: Learn from skill usage and update weights
################################################################################

set -e

# Get tool name
TOOL_NAME="$1"
EXIT_CODE="$2"  # 0 = success, non-zero = failure

# Only process Skill tool usage
if [[ "$TOOL_NAME" != "Skill" ]]; then
    exit 0
fi

# Get skill name from tool arguments
SKILL_NAME="$3"

# Get last user input
TEMP_DIR="${CLAUDE_TEMP_DIR:-/tmp}"
LAST_INPUT_FILE="$TEMP_DIR/last_user_input.txt"

if [ ! -f "$LAST_INPUT_FILE" ]; then
    exit 0
fi

USER_INPUT=$(cat "$LAST_INPUT_FILE")

# Determine if this was a successful skill invocation
WAS_SUCCESSFUL=false
if [ "$EXIT_CODE" -eq 0 ]; then
    WAS_SUCCESSFUL=true
fi

# Determine if user accepted a recommendation
# (This needs to be tracked by the hook system)
USER_ACCEPTED=false
if [ -f "$TEMP_DIR/recommendation_accepted.txt" ]; then
    USER_ACCEPTED=true
    rm "$TEMP_DIR/recommendation_accepted.txt"
fi

# Calculate weight change
if [ "$USER_ACCEPTED" = "true" ]; then
    WEIGHT_CHANGE="+0.10"
elif [ "$WAS_SUCCESSFUL" = "true" ]; then
    WEIGHT_CHANGE="+0.05"
else
    WEIGHT_CHANGE="-0.05"
fi

# Save learning pattern to memory
LEARNING_ENTRY=$(cat <<EOF
[LEARNING_PATTERN]
Skill: $SKILL_NAME
Trigger: $USER_INPUT
Action: $([ "$USER_ACCEPTED" = "true" ] && echo "accepted_recommendation" || echo "manual_invocation")
Successful: $WAS_SUCCESSFUL
Weight Change: $WEIGHT_CHANGE
Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
)

# Save to memory (via MCP or API)
curl -s -X POST \
  "http://localhost:18000/memos/save" \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": $(echo "$LEARNING_ENTRY" | jq -Rs .),
    \"cube_id\": \"dev_cube\",
    \"memory_type\": \"LEARNING_PATTERN\"
  }" > /dev/null 2>&1 || true

# Clean up
rm -f "$LAST_INPUT_FILE"

exit 0
```

### PowerShell Implementation

**File:** `.claude/hooks/powershell/PostToolUse.ps1`

```powershell
################################################################################
# PostToolUse Hook - Skill Learning System (PowerShell)
################################################################################

param(
    [Parameter(Mandatory=$true)]
    [string]$ToolName,

    [Parameter(Mandatory=$true)]
    [int]$ExitCode
)

# Only process Skill tool usage
if ($ToolName -ne "Skill") {
    exit 0
}

# Get skill name from tool arguments
$SkillName = $args[2]

# Get last user input
$TempDir = $env:CLAUDE_TEMP_DIR ?? $env:TEMP
$LastInputFile = Join-Path $TempDir "last_user_input.txt"

if (-not (Test-Path $LastInputFile)) {
    exit 0
}

$UserInput = Get-Content $LastInputFile -Raw

# Determine success
$WasSuccessful = ($ExitCode -eq 0)

# Determine if user accepted recommendation
$UserAccepted = $false
$RecAcceptedFile = Join-Path $TempDir "recommendation_accepted.txt"
if (Test-Path $RecAcceptedFile) {
    $UserAccepted = $true
    Remove-Item $RecAcceptedFile -Force
}

# Calculate weight change
$WeightChange = if ($UserAccepted) {
    "+0.10"
} elseif ($WasSuccessful) {
    "+0.05"
} else {
    "-0.05"
}

# Save learning pattern
$LearningEntry = @"
[LEARNING_PATTERN]
Skill: $SkillName
Trigger: $UserInput
Action: $(if ($UserAccepted) { "accepted_recommendation" } else { "manual_invocation" })
Successful: $WasSuccessful
Weight Change: $WeightChange
Timestamp: $((Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"))
"@

# Save to memory
try {
    $Payload = @{
        content = $LearningEntry
        cube_id = "dev_cube"
        memory_type = "LEARNING_PATTERN"
    } | ConvertTo-Json -Compress

    Invoke-RestMethod -Uri "http://localhost:18000/memos/save" `
        -Method POST `
        -ContentType "application/json" `
        -Body $Payload | Out-Null
} catch {
    # Ignore API errors
}

# Clean up
Remove-Item $LastInputFile -Force -ErrorAction SilentlyContinue

exit 0
```

---

## PreToolUse Hook (Optional)

**Purpose:** Intercept tool calls before execution

```bash
#!/bin/bash
# .claude/hooks/bash/pre-tool-use.sh

TOOL_NAME="$1"

# Example: Block certain tool combinations
if [[ "$TOOL_NAME" == "Skill" ]]; then
    # Check if skill conflicts with running state
    # ...
    true
fi

exit 0
```

---

## Stop Hook (Optional)

**Purpose:** Final cleanup and verification when session ends

```bash
#!/bin/bash
# .claude/hooks/bash/stop.sh

# Flush any pending learning data
# Generate usage statistics
# Clean up temporary files

exit 0
```

---

## Configuration File

**Location:** `~/.claude/config/skill-trigger-config.json`

```json
{
  "enabled": true,
  "confidence_threshold": 0.6,
  "max_recommendations": 5,
  "auto_trigger": false,
  "learning_mode": true,
  "user_preferences": {
    "show_recommendations": true,
    "show_explanation": true,
    "show_confidence": false,
    "color_output": true
  },
  "performance": {
    "enable_caching": true,
    "cache_ttl": 3600,
    "async_queries": true
  }
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMOS_DEFAULT_CUBE` | `dev_cube` | Default memory cube ID |
| `MEMOS_URL` | `http://localhost:18000` | MemOS API URL |
| `CLAUDE_TEMP_DIR` | `/tmp` | Temporary directory for hook data |
| `SKILL_TRIGGER_DEBUG` | `false` | Enable debug logging |

---

## Debugging

### Enable Debug Mode

```bash
export SKILL_TRIGGER_DEBUG=true
```

### Check Hook Logs

```bash
# Bash hooks
cat ~/.claude/logs/hooks.log

# PowerShell hooks
cat ~/.claude/logs/powershell-hooks.log
```

### Test Hook Manually

```bash
# Test UserPromptSubmit hook
echo "Write tests for login" | .claude/hooks/bash/user-prompt-submit.sh

# Test PostToolUse hook
.claude/hooks/bash/post-tool-use.sh "Skill" 0 "tdd-guide"
```

---

## Hook Execution Flow

```
User Input
    ↓
[UserPromptSubmit Hook]
    ├─ Parse user input
    ├─ Get conversation history
    ├─ Search memory for skills
    ├─ Filter by confidence
    └─ Display recommendations
    ↓
User Invokes Skill (or ignores)
    ↓
[PreToolUse Hook] (optional)
    ├─ Validate parameters
    └─ Check conflicts
    ↓
[Tool Execution]
    ↓
[PostToolUse Hook]
    ├─ Record skill usage
    ├─ Update weights
    └─ Save learning pattern
    ↓
[Session Ends]
    ↓
[Stop Hook] (optional)
    └─ Cleanup and generate reports
```

---

## Troubleshooting

### Hook Not Executing

**Symptom:** Recommendations not showing

**Solutions:**
1. Check hook file permissions: `chmod +x .claude/hooks/bash/*.sh`
2. Verify hook path in `~/.claude/settings.json`
3. Enable debug mode: `export SKILL_TRIGGER_DEBUG=true`
4. Check API connectivity: `curl http://localhost:18000/health`

### API Timeout

**Symptom:** Hook hangs or is slow

**Solutions:**
1. Increase timeout in hook script
2. Enable caching in config
3. Check MemOS server is running
4. Use async queries (Python hook)

### Incorrect Recommendations

**Symptom:** Wrong skills recommended

**Solutions:**
1. Adjust `confidence_threshold` in config
2. Add more trigger keywords to skill metadata
3. Review learning patterns in memory
4. Manually annotate problematic skills

---

## Best Practices

1. **Keep hooks lightweight** - Minimize API calls and processing
2. **Use local caching** - Cache frequently accessed data
3. **Fail gracefully** - Don't break if API is unavailable
4. **Log everything** - Enable debug mode during development
5. **Test thoroughly** - Test hooks with various inputs before deployment
6. **Version control** - Keep hooks under git
7. **Document changes** - Maintain changelog for hook updates

---

**Reference Version:** 1.0
**Last Updated:** 2026-01-31
