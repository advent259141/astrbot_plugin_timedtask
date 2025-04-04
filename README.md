</div>

<div align="center">

![:name](https://count.getloli.com/@astrbot_plugin_timedtask?name=astrbot_plugin_timedtask&theme=booru-lewd&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

</div>

# AstrBot 定时任务插件

一个简单易用的群聊定时任务提醒插件，可以设置每日定时提醒。

## 功能特点

- 设置每日固定时间的提醒
- 支持多种时间输入格式（传统格式、数字格式、冒号格式）
- 统一的时间显示格式，便于阅读
- 查看当前会话的所有定时任务
- 删除指定的定时任务并自动重排序
- 任务持久化保存，重启不丢失
- 10秒检查周期，定时提醒更准确
- 倒计时功能，为任务设置有效天数并自动结束
- AT功能，提醒时自动@指定用户
- 图片功能，可在任务中包含图片，提醒时自动发送
- 群聊独立编号，不同群聊任务ID互不影响

## 使用方法

### 帮助指令

显示插件的所有指令和使用说明。

```
timedtask_help
```

### 设置任务

设置一个每天固定时间的提醒任务。支持多种时间格式：

```
设置任务 8时30分 早会提醒
设置任务 0830 早会提醒
设置任务 08:30 早会提醒
```
### 设置任务

设置一个每天固定时间的提醒任务。支持多种时间格式：

```
设置任务 8时30分 早会提醒
设置任务 0830 早会提醒
设置任务 08:30 早会提醒
```

也可以在任务内容中@某人，这样在提醒时会自动AT该用户：

```
设置任务 8时30分 早会准备好了吗？ @张三
```

还可以在设置任务时附带图片，这些图片会在提醒时一并发送：

```
设置任务 8时30分 会议资料 [图片]
```

无论输入哪种格式，系统都会统一以"小时时分钟分"的标准格式显示。

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
