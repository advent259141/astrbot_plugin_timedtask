</div>

<div align="center">

![:name](https://count.getloli.com/@astrbot_plugin_timedtask?name=astrbot_plugin_timedtask&theme=booru-lewd&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

</div>

# AstrBot 定时任务插件

一个简单易用的群聊定时任务提醒插件，可以设置每日定时提醒。

## 功能特点

- 设置每日固定时间的提醒
- 查看当前会话的所有定时任务
- 删除指定的定时任务
- 任务持久化保存，重启不丢失
- 10秒检查周期，定时提醒更准确

## 使用方法

### 设置任务

设置一个每天固定时间的提醒任务。

```
设置任务 8时30分 早会提醒
```

### 查看任务列表

列出当前会话的所有定时任务。

```
任务列表
```

### 删除任务

删除指定ID的定时任务。

```
删除任务 1
```

## 技术实现

- 异步任务处理，不阻塞主线程
- 使用 unified_msg_origin 确保消息发送到正确的会话
- JSON 文件持久化存储任务信息
- 优化的定时任务检测机制，避免重复执行

## 配置文件

任务数据保存在插件目录下的 `tasks.json` 文件中，格式如下：

```json
{
  "tasks": {
    "umo_string": [
      ["8时30分", "早会提醒", 1],
      ["12时0分", "午餐时间", 2]
    ]
  },
  "next_task_id": 3
}
```

## 许可证

MIT License

## 作者

AstrBot Team
