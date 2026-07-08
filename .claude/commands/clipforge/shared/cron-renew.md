# ClipForge 共享：定时任务自续期

> **无论管线执行成功或失败，都必须执行续期。** 续期是保持定时任务存活的机制，与本次执行结果无关。

## §1 cron 表达式来源

从 memory 的 `cron-schedules.md` 读取对应任务的 cron 表达式。如果 memory 中无配置，使用编排文件中指定的默认值。

## §2 任务关键词匹配

> 动态匹配：在 CronList 结果中搜索 `prompt` 字段包含 `<任务关键词>` 的 job。
> 任务关键词由调用方传入（如 `github-daily-trending`、`finance-weekly` 等），不在此处硬编码。

**匹配规则**：
1. CronList 列出所有定时任务
2. 在每个 job 的 `prompt` 字段中搜索包含任务关键词的条目
3. 如找到多个同关键词 job，全部标记为旧 job 待清理
4. 创建新 job 后删除所有旧 job，确保最终只剩 1 个

## §3 模式（先创建后删除，保证原子性）

> **原则：先建后拆。** 新 job 创建成功前不删除旧 job，避免删除成功但创建失败导致任务丢失。

```
1. 从 memory cron-schedules.md 读取对应任务的 cron 表达式
   - 如 memory 中无配置，使用编排文件中指定的默认值
   - 如也无默认值，报错终止
2. CronList 列出所有定时任务
   - 如 CronList 失败或返回空，记录警告并重试（最多 2 次）
3. 找到 prompt 包含 "<任务关键词>" 的所有旧 job
4. CronCreate 创建新任务（使用读到的 cron 表达式，**durable: true**）
   > ⛔ HARD：`durable` 必须**显式传 `true`**。CronCreate 默认 `durable:false`（session-only），会话退出任务即蒸发——续期漏传 durable 是定时任务静默丢失的根因（无报错无告警，靠 SessionStart hook 自愈兜底）。
5. 确认新 job 创建成功（记录 new_job_id）
6. 逐个 CronDelete 删除步骤 3 找到的旧 job（排除刚创建的 new_job_id）
7. 再次 CronList 确认只有 1 个该类型任务存在
8. 如果确认时发现 > 1 个同关键词任务，重复步骤 6-7（最多 3 轮）
9. 超过重试上限后仍有重复，记录错误并终止
```

## §4 输出模板

```
✅ <任务名>已自续期 7 天（旧任务已清理）
Job ID: <new_job_id>
下次触发: <下次触发时间描述>
```
