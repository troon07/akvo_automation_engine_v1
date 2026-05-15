# Engineering Learnings & Root Cause Notes

## 1. Timezone Bug — Offline Detection

Issue:
Offline detection never triggered.

Root Cause:
Manual timestamps were entered assuming IST, but Supabase stored/interpreted timestamps in UTC.

Impact:
Machines appeared to have future timestamps.
offline_duration became negative.
Offline automation never triggered.

Resolution:
Used PostgreSQL:
```sql
NOW() - INTERVAL '20 minutes'
```
instead of manually typing timestamps.

Lesson:
- Always test timestamps using database-generated UTC time.
- Never manually type timestamps during testing.
- Timezone bugs are extremely common in monitoring systems.

---

## 2. Supabase URL Misconfiguration

Issue:
RPC queries failed.

Root Cause:
SUPABASE_URL incorrectly included:
```txt
/rest/v1
```

Resulting URL:
```txt
/rest/v1/rest/v1
```

Resolution:
Use only:
```txt
https://project.supabase.co
```

Lesson:
Always provide base Supabase URL only.

---

## 3. Offline Recovery PATCH Spam

Issue:
resolve_alert() executed every scheduler cycle.

Impact:
- unnecessary PATCH requests
- noisy logs
- poor scaling behavior

Root Cause:
Recovery logic attempted resolution without checking unresolved alert existence.

Resolution:
Added:
```python
has_unresolved_alert()
```
helper.

Lesson:
Avoid unnecessary write operations in recurring automations.

---

## 4. Scheduler Reload CancelledError

Issue:
CancelledError appeared during development.

Root Cause:
Uvicorn reload interrupted APScheduler jobs mid-execution.

Lesson:
Normal development behavior.
Not a production failure.

---

## 5. Latest-State Query Testing Mistake

Issue:
Offline testing initially failed.

Root Cause:
Edited rows were not necessarily latest rows.
Automation checks only latest timestamp per machine.

Lesson:
Always verify actual query results when debugging automation behavior.

---

## 6. Codex Duplicate Docstrings

Issue:
Codex repeatedly generated duplicate function docstrings.

Lesson:
Always manually review generated code.
AI-generated code is not automatically production-ready.

---

## 7. Context Continuity vs Model Switching

Observation:
Switching models mid-implementation can reduce architectural consistency.

Lesson:
- Keep same model during active implementation session.
- Use smaller models for isolated small tasks.
- Use stronger models for architecture/debugging.

---

## 8. Automation Validation Principle

Important Learning:
Code generation is NOT validation.

Correct Workflow:
```txt
build
↓
test
↓
observe runtime behavior
↓
validate edge cases
↓
optimize
```

Lesson:
Always validate automation behavior with controlled tests.

---

## 9. Rule-Based Logic Before AI

Observation:
Simple rules solved current operational problems effectively.

Lesson:
Do NOT introduce AI when:
- thresholds work
- state transitions work
- deterministic rules are enough

AI should only be added when measurable value exists.

---

## 10. Shared Alert Infrastructure Was Correct Decision

Observation:
Using common alert lifecycle functions across automations simplified architecture.

Benefits:
- reusable logic
- consistent alert behavior
- easier maintenance
- scalable automation framework

Lesson:
Centralized alert lifecycle management is critical for monitoring systems.

---

## 11. Real Engineering Progression

Validated Engineering Sequence:
```txt
make it work
↓
make it reliable
↓
make it efficient
↓
then scale
```

Lesson:
Do NOT prematurely optimize or overengineer.

---

## 12. Git & GitHub Importance

Observation:
Stable checkpoints became critical once multiple automations existed.

Lesson:
Use:
- Git for local version control
- GitHub for backup/history

Commit after stable milestones, not after random incomplete edits.

## 13. Sequence Validation Is More Complex Than Threshold Monitoring

Observation:
Temporal operational rules are significantly more subtle than simple threshold alerts.

Examples:
- startup timing
- shutdown timing
- continuous state validation
- transition detection

Lesson:
Sequence/state-machine automations require:
- careful transition analysis
- runtime validation
- edge-case testing
- sparse telemetry consideration

They should not be implemented casually.

## 14. Transition-Based Logic Scales Better Than Raw Row Validation

Observation:
Using compressor state transitions produced cleaner automation logic than checking every raw row continuously.

Benefits:
- reduced complexity
- clearer operational reasoning
- lower query cost
- easier debugging

Lesson:
For behavioral automations, prefer event/transition detection over brute-force row scanning where practical.

## 15. Runtime Validation Is More Important As Automation Complexity Increases

Observation:
As automations became temporal and sequence-aware, code review alone became insufficient.

Lesson:
Complex operational automations must be validated with controlled runtime scenarios, not just syntax checks or static review.

## 16. Overlapping Operational Rules Can Trigger Multiple Valid Alerts

Observation:
A single machine behavior may violate multiple operational rules simultaneously.

Example:
compressor ON while fan OFF:
- runtime mismatch
- improper startup sequence

Lesson:
Operational alert systems may require future alert prioritization or suppression rules to reduce alert noise.

Current Decision:
Runtime mismatch is treated as the more operationally critical condition.

## 17. Conservative Operational Validation Is Preferable To Aggressive False Alerts

Observation:
Startup sequence validation avoided triggering under uncertain telemetry history.

Lesson:
In industrial monitoring systems:
- false positives reduce operator trust
- conservative validation is often safer than aggressive alerting

Operational reliability is more important than maximum detection sensitivity.


## 18. Deterministic Simulators Are Better Than Random Telemetry Generators

Observation:
Deterministic operational scenarios produced far more reliable automation validation than random telemetry generation would.

Benefits:
- reproducible bugs
- predictable automation behavior
- easier debugging
- stable testing

Lesson:
Testing infrastructure should prioritize reproducibility over randomness during early-stage backend development.


## 20. Always Interpret Diffs Correctly Before Assuming Code Failure

Observation:
Git/Codex diff views display removed and added code simultaneously.

Initial interpretation incorrectly assumed duplicated arguments existed in final code.

Lesson:
Before diagnosing AI-generated code failures:
- understand diff visualization
- distinguish removed vs added lines
- inspect final file state when uncertain


## 22. Indexing Should Follow Real Query Patterns, Not Premature Assumptions

Observation:
Indexes became valuable only after:
- multiple automations existed
- historical scans existed
- alert lifecycle queries increased

Lesson:
Add indexes based on actual query behavior and operational patterns, not speculative optimization.


## 23. Health Endpoints Should Validate Infrastructure, Not Business Logic

Observation:
A lightweight health endpoint provides far more reliable operational visibility than heavy application-level checks.

Lesson:
Health endpoints should:
- validate infrastructure availability
- remain lightweight
- avoid historical scans
- avoid business analytics queries

Fast and reliable health checks are critical for production systems.


## 25. Lightweight Runtime Metrics Provide Huge Operational Value

Observation:
Simple in-memory execution metrics provided strong operational visibility without requiring external monitoring infrastructure.

Benefits:
- execution visibility
- failure tracking
- runtime diagnostics
- scheduler observability

Lesson:
Operational insight can often be achieved with lightweight internal instrumentation before adopting large monitoring stacks.


## 26. Execution Duration Metrics Reveal Scaling Risk Early

Observation:
Automation execution metrics exposed real runtime costs long before large-scale deployment.

Benefits:
- early bottleneck visibility
- scheduler performance insight
- historical query cost awareness

Lesson:
Basic execution timing instrumentation is one of the highest-value low-complexity observability features in backend systems.



