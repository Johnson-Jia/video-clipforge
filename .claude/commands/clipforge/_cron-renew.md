---
name: cron-renew
description: 定时任务自续期 — 确保自动化定时任务持续运行
version: "1.0.0"
type: EXECUTIVE
rigor: STRICT
dependencies: []
---

# ClipForge 共享：定时任务自续期

## Intent
> 确保定时任务持续运行。
> 成功标准：新任务已创建并激活，旧重复任务已清理，仅保留 1 个活跃任务。

## Boundary — 行为准则

### 必须遵守（HARD 规则 · 正向重述）

1. **先建后拆** — 新 job 创建成功前不删除旧 job，保证原子性 ← `R-CRON-001`
   ↳ 校验：CronDelete 在 CronCreate 确认成功之后执行
2. **无条件执行** — 无论管线执行成功或失败，都必须执行续期 ← `R-CRON-002`
   ↳ 校验：续期在每次执行末尾无条件触发
3. **验证唯一性** — 续期后 CronList 确认只有 1 个同关键词任务存在 ← `R-CRON-003`
   ↳ 校验：CronList 输出中同关键词任务数量 = 1

### 建议参考
- 无

## Guard — 认知守卫

| 当你产生这个念头 | 现实是 | 触发行为 |
|---|---|---|
| "管线失败了，不用续期" | 续期与本次执行结果无关，不续期 = 定时任务永久死亡 | 无条件执行续期 |
| "先删旧的再建新的更快" | 删成功但建失败 = 任务丢失，无人知晓 | 坚持先建后拆 |
| "创建成功就行了，不用验证" | 可能出现多个同关键词任务导致重复触发 | 执行 CronList 验证 |

### Spirit vs Letter

| 规则 | 模式 | 真实意图 |
|---|---|---|
| R-CRON-001 | SPIRIT | 确保定时任务在任何时刻都至少有一个活跃实例 |

## Gate — 通过标准

### 流程门禁（自动化检查，不通过 = 重试，max_retries: 1）
- [ ] `cron_active` — CronList 确认新任务存在且 cron 表达式正确
- [ ] `unique_job` — CronList 确认同关键词任务数量为 1

## Trace — 采集点
- **执行开始**：记录任务关键词、cron 表达式来源
- **执行结束**：记录旧 job ID、新 job ID、下次触发时间
- **写入**：`{project_dir}/trace/cron-renew-{timestamp}.yaml`

## 操作指令

### cron 表达式来源

从 memory 的 `cron-schedules.md` 读取对应任务的 cron 表达式。如果 memory 中无配置，使用编排文件中指定的默认值。

### 任务关键词映射

| 任务关键词 | COMMAND |
|-----------|---------|
| `github-daily-trending` | `/github-daily-trending` |
| `github-weekly-trending` | `/github-weekly-trending` |
| `github-weekly-zhihu` | `/github-weekly-zhihu` |

### 执行流程（先建后拆，保证原子性）

```
1. 从 memory cron-schedules.md 读取对应任务的 cron 表达式
2. CronList 列出所有定时任务
3. 找到 prompt 包含 "<任务关键词>" 的所有旧 job
4. CronCreate 创建新任务（使用读到的 cron 表达式，durable: true）
5. 确认新 job 创建成功（记录 new_job_id）
6. 逐个 CronDelete 删除步骤 3 找到的旧 job（排除刚创建的 new_job_id）
7. 再次 CronList 确认只有 1 个该类型任务存在
8. 如果确认时发现 > 1 个同关键词任务，重复步骤 6-7
```

### 输出模板

```
✅ <任务名>已自续期 7 天（旧任务已清理）
Job ID: <new_job_id>
下次触发: <下次触发时间描述>
```

## Red Flags

| 信号 | 说明 |
|------|------|
| 管线失败后跳过续期 | 续期与执行结果无关，跳过 = 定时任务永久死亡 |
| 先删旧任务再建新任务 | 删成功建失败 = 任务丢失 |
| 续期后不验证 | 多任务重复触发导致并行冲突 |

## Common Rationalizations

| 借口 | 事实 |
|------|------|
| "这次失败了就不续期了" | 续期是保活机制，与本次执行结果无关 |
| "先删后建更快" | 原子性保证：新 job 创建成功前不删旧 job |
| "CronCreate 成功了就行" | 必须 CronList 验证唯一性，防止重复触发 |
