# Technical Debt & Deferred Improvements

## High Priority

### 1. Add database indexes for scaling
Status: Deferred
Priority: High

Problem:
Historical queries on esp_sensor_data will become expensive as data volume grows.

Current Risk:
- Slow automation execution
- Increased Supabase query latency
- Higher database CPU usage

Recommended Future Fix:
Add indexes:
```sql
CREATE INDEX idx_esp_sensor_data_machine_time
ON esp_sensor_data(machine_id, esp_log_at DESC);

CREATE INDEX idx_esp_sensor_data_time
ON esp_sensor_data(esp_log_at DESC);
```

Reason Deferred:
Current dataset is too small to justify optimization.

---

### 2. Rapid cycling auto-resolution edge case
Status: Deferred
Priority: Medium

Problem:
Rapid cycling alerts only resolve for machines that still appear in recent rows.

Edge Case:
If machine stops sending rows entirely:
- rows_by_machine will not include it
- rapid cycling alert may remain unresolved forever

Recommended Future Fix:
Introduce machine registry/state management.

Reason Deferred:
Current single-machine testing environment does not require it.

---

### 3. Scheduler observability
Status: Deferred
Priority: Medium

Problem:
Scheduler currently lacks:
- execution metrics
- automation duration tracking
- failure counters
- health dashboard

Future Improvement:
Add:
- structured automation metrics
- execution timing
- automation health monitoring

Reason Deferred:
Premature for current scale.

---

### 4. Structured logging
Status: Deferred
Priority: Medium

Problem:
Current logs are plain-text only.

Future Improvement:
Use structured JSON logging.

Benefits:
- easier debugging
- centralized monitoring
- log aggregation
- production observability

Reason Deferred:
Not necessary for local development.

---

### 5. Machine registry table
Status: Deferred
Priority: Medium

Problem:
Machines are currently inferred from sensor data only.

Future Improvement:
Create dedicated machines table:
- machine metadata
- machine health state
- deployment info
- firmware version
- location

Reason Deferred:
Current testing uses single-machine architecture.

---

### 6. Automation execution persistence
Status: Deferred
Priority: Medium

Problem:
APScheduler state is currently in-memory only.

Risk:
Server restart loses runtime scheduling state.

Future Improvement:
Use persistent scheduler backend.

Reason Deferred:
Current automations are interval-based and restart safely.

---

### 7. Alert rate limiting
Status: Deferred
Priority: Medium

Problem:
Future automations may generate excessive alerts.

Future Improvement:
Add:
- cooldown windows
- alert suppression
- alert aggregation

Reason Deferred:
Current automation count is small.

---

### 8. Partitioning strategy for large datasets
Status: Deferred
Priority: Low

Problem:
esp_sensor_data will grow extremely large at production scale.

Future Improvement:
Use:
- PostgreSQL partitioning
- TimescaleDB
- cold storage strategy

Reason Deferred:
Far too early.

---

### 9. Codex-generated cleanup inconsistencies
Status: Ongoing
Priority: Low

Observed Issues:
- duplicate docstrings
- inconsistent imports
- occasional redundant logic

Rule:
Always manually review generated code before accepting.

---

### 10. Better offline simulation tooling
Status: Deferred
Priority: Low

Problem:
Testing currently depends on manual SQL updates.

Future Improvement:
Create:
- local simulator
- fake telemetry generator
- test automation harness

Reason Deferred:
Current manual testing is sufficient.

---
## 11. Startup sequence validation may be too strict
Status: Deferred
Priority: Medium

Problem:
Startup validation currently requires all telemetry rows in the 5-minute lead window to show fan_status = ON.

Risk:
Sparse telemetry or missed packets may create false startup violations.

Future Improvement:
Use state-duration validation instead of strict all-row validation.

Reason Deferred:
Current telemetry frequency is stable enough for V1.

## 12. Sequence validation lacks machine mode awareness
Status: Deferred
Priority: Medium

Problem:
Fan/compressor sequence validation ignores machine operating mode.

Risk:
Future maintenance/service/testing modes may intentionally violate normal sequencing rules and generate false alerts.

Future Improvement:
Make validation rules mode-aware.

Reason Deferred:
Current system uses only normal operating mode.

## 13. Shutdown validation depends on telemetry density
Status: Deferred
Priority: Medium

Problem:
Shutdown sequence validation assumes sufficient telemetry exists during post-cooling window.

Risk:
Sparse telemetry may create false shutdown alerts or false resolutions.

Future Improvement:
Use state-transition tracking instead of row-density assumptions.

Reason Deferred:
Current telemetry interval is acceptable for V1.


## 14. Startup validation currently conservative under insufficient telemetry
Status: Deferred
Priority: Medium

Problem:
Startup sequence validation may skip alert generation when historical telemetry is insufficient.

Current Behavior:
System prefers avoiding false positives over aggressive startup violation detection.

Risk:
Some real startup violations may not trigger alerts.

Future Improvement:
Implement state-duration tracking independent of row density.

Reason Deferred:
Current conservative behavior is safer for operational trust.


## 15. Simulator currently inserts all scenario rows immediately
Status: Deferred
Priority: Low

Problem:
Simulator inserts all scenario telemetry rows in a single batch rather than streaming over real time.

Risk:
Timing-sensitive automations may behave slightly differently from real ESP behavior.

Future Improvement:
Optional real-time telemetry replay mode.

Reason Deferred:
Timestamp simulation is currently sufficient for backend validation.


## Sensor Freeze Detection Scalability

Current V1 sensor freeze detection fetches bounded recent telemetry rows and groups them in memory by machine.

This is acceptable for current scale and early operational development.

At larger fleet scale (1000–10000 machines), this approach may require optimization:
- pre-aggregated telemetry windows
- machine-batched analysis
- streaming aggregation
- edge-side temporal analysis

Current architecture intentionally prioritizes:
- simplicity
- correctness
- conservative operational intelligence
over premature optimization.

## Automation Execution Observability

Current execution observability stores summary-level automation execution metrics:
- duration
- analyzed machine count
- detection count
- status
- error visibility

This is intentionally lightweight and scalable.

Future improvements MAY include:
- execution trend aggregation
- automation performance dashboards
- noisy automation detection
- automation usefulness scoring

Current implementation intentionally avoids:
- verbose traces
- telemetry-level logging
- distributed tracing
- heavy observability frameworks

to preserve operational simplicity and scalability.