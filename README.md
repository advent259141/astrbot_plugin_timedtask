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

### 帮助指令

显示插件的所有指令和使用说明。

```
timedtask_help
```

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

### 设置任务倒计时

设置任务的倒计时天数，倒计时结束后任务将自动停止提醒。

```
设置倒计时 1 30
```

上面的命令表示将任务ID为1的提醒设置为30天倒计时，每天发送提醒时会显示剩余天数，倒计时结束后任务自动删除。


### 删除任务

删除指定ID的定时任务。

```
删除任务 1
```
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

Jason.Joestar
