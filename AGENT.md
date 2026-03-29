# AGENT RULES

You are an autonomous coding agent working on this repository.

## 🔴 Mandatory Behavior

### 1. Logging is REQUIRED

After EVERY meaningful coding step:

1. Generate a structured step log:

### [HH:MM] Step: <short description>

- Action: <what you did>
- Files: <files modified>
- Reason: <why>
- Result: <outcome>
- Next: <next step>

---

2. Save to temp file:

temp_log.txt

---

3. Execute:

python src/obsidian_logger.py temp_log.txt AlphaForge

---

### 2. Always read memory first

Before starting ANY task:

- Read:
  - 01 Projects/AlphaForge/worklog.md
  - Daily/<today>.md (if exists)

---

### 3. Never skip logging

Logging is mandatory.

---

### 4. Continue work, do not restart

Always build on previous progress.

## 🧠 Memory First Rule (MANDATORY)

Before starting ANY task:

1. Execute:

python scripts/read_memory.py

2. Read and understand:
- What has already been done
- Current progress
- Next pending tasks

3. Then proceed with implementation

---

DO NOT start coding before reading memory.

### 🚨 CRITICAL: Logging Enforcement

If you ever complete work WITHOUT logging:

You MUST immediately:
1. reconstruct all steps you performed
2. generate missing logs
3. write them to Obsidian

Logging is NOT optional and must be consistent with actual work performed.

### Logging Completion Rule

Logging is NOT complete when temp_log.txt is created.

Logging is complete ONLY if all of the following are true:
1. temp_log.txt is generated
2. python src/obsidian_logger.py temp_log.txt AlphaForge is executed
3. the write to Obsidian succeeds
4. Daily and project worklog are updated

If any step fails, you must report the failure explicitly and stop claiming logging is complete.
If temp_log.txt exists but Obsidian has not been updated, you must treat this as an incomplete task and immediately finish the write step.