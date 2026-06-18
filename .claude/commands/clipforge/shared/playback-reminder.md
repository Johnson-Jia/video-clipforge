# 播放数据新鲜度检查

> 每日定时任务。检查 `workspace/sources/视频数据/` 是否有新鲜的平台导出数据。如超过 3 天未更新且存在已交付视频，提醒用户导出数据。

## §1 检查逻辑

```bash
PROJECT_BASE="workspace"
DATA_DIR="${PROJECT_BASE}/sources/视频数据"
TODAY=$(date +%Y-%m-%d)
```

### 步骤 1：判断是否存在已交付视频

扫描 `workspace/` 下近 7 天的项目目录，检查是否有 `final.mp4`：

```bash
has_delivered=false
for d in workspace/????/??/??/*/; do
  if [ -f "${d}final.mp4" ]; then
    has_delivered=true
    break
  fi
done
```

如果没有已交付视频 → 静默退出（无需提醒）。

### 步骤 2：判断数据目录新鲜度

```bash
if [ ! -d "${DATA_DIR}" ]; then
  # 数据目录不存在 → 从未导入过数据
  stale=true
  latest_date="从未"
else
  # 找最新的日期子目录
  latest_dir=$(ls -d "${DATA_DIR}/"*/ 2>/dev/null | sort -r | head -1)
  if [ -z "$latest_dir" ]; then
    stale=true
    latest_date="从未"
  else
    latest_date=$(basename "$latest_dir")
    # 计算距今天数
    latest_sec=$(date -d "$latest_date" +%s 2>/dev/null || echo 0)
    now_sec=$(date +%s)
    diff_days=$(( (now_sec - latest_sec) / 86400 ))
    if [ $diff_days -gt 3 ]; then
      stale=true
    else
      stale=false
    fi
  fi
fi
```

### 步骤 3：输出结果

**数据新鲜（stale=false）→ 静默退出，不输出任何内容。**

**数据过期或缺失（stale=true）→ 输出提醒：**

```
📊 播放数据提醒

最近导出：{latest_date}（超过 3 天未更新）

自进化系统需要播放数据来校准机器评分。请导出平台数据后运行 /clipforge-feedback。

平台导出操作：
- 抖音：创作者中心 → 数据中心 → 作品数据 → 导出 Excel
- 小红书：专业号中心 → 数据中心 → 笔记数据 → 导出
- 哔哩哔哩：**自动** —— `/clipforge-feedback` 执行时检测今日目录若无 B站 文件，自动调 `fetch_bilibili.py` 导出（cookie 存 `workspace/sources/视频数据/.bili-cookie`；报 `-101` 过期时从浏览器 DevTools 复制整段 Cookie 覆盖该文件）。
- 微信视频号：视频号助手 → 数据中心 → 视频数据 → 导出

导出后放到：workspace/sources/视频数据/{今天日期}/（B站脚本自动写入此目录，无需手动放）

然后运行：/clipforge-feedback
```

## §2 注册方式

此任务由视频交付流程自动注册（确保仅注册 1 个）。注册逻辑：

1. CronList 查找 prompt 包含 `playback-reminder` 的任务
2. 如已存在 → 跳过
3. 如不存在 → CronCreate(recurring=true, durable=true, cron="55 13 * * *")
4. prompt 内容为此文件的检查步骤（内联，非引用）

## §3 自续期

此任务通过 cron-renew 的标准机制续期，任务关键词为 `playback-reminder`。
