# ClipForge 共享：定时任务自续期

> **无论管线执行成功或失败，都必须执行续期。** 续期是保持定时任务存活的机制，与本次执行结果无关。

## cron 表达式来源

从 memory 的 `cron-schedules.md` 读取对应任务的 cron 表达式。如果 memory 中无配置，使用编排文件中指定的默认值。

## 任务关键词映射

| 任务关键词 | COMMAND |
|-----------|---------|
| `github-daily-trending` | `/github-daily-trending` |
| `github-weekly-trending` | `/github-weekly-trending` |
| `github-weekly-zhihu` | `/github-weekly-zhihu` |

## 模式（先创建后删除，保证原子性）

> **原则：先建后拆。** 新 job 创建成功前不删除旧 job，避免删除成功但创建失败导致任务丢失。

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

## 输出模板

```
✅ <任务名>已自续期 7 天（旧任务已清理）
Job ID: <new_job_id>
下次触发: <下次触发时间描述>
```
