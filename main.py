import re
import time
import datetime
import asyncio
import threading
import json
import os
from typing import Dict, List, Tuple, Set

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.event import MessageChain

@register("timedtask", "astrbot", "一个群聊定时任务提醒插件", "1.0.0", "https://github.com/yourusername/astrbot_plugin_timedtask")
class TimedTaskPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.tasks = {}  # 格式: {umo: [(time_str, content, task_id), ...]}
        self.next_task_id = 0
        self.task_running = True
        self.executed_tasks = set()  # 记录已执行过的任务，避免重复执行
        self.last_day = datetime.datetime.now().day  # 记录上次执行的日期
        
        # 任务保存路径
        self.save_path = os.path.join(os.path.dirname(__file__), "tasks.json")
        
        # 加载保存的任务
        self.load_tasks()
        
        # 异步启动任务检查器
        asyncio.create_task(self.check_tasks())
        print("定时任务插件已加载")

    def parse_time(self, time_str: str) -> Tuple[int, int]:
        """解析时间字符串，格式为 xx时xx分"""
        pattern = r'(\d+)时(\d+)分'
        match = re.match(pattern, time_str)
        if not match:
            raise ValueError("时间格式错误，请使用 xx时xx分 的格式")
        
        hour = int(match.group(1))
        minute = int(match.group(2))
        
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("时间范围错误，小时应在0-23之间，分钟应在0-59之间")
        
        return hour, minute

    def load_tasks(self):
        """从文件加载任务"""
        try:
            if os.path.exists(self.save_path):
                with open(self.save_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = data.get("tasks", {})
                    self.next_task_id = data.get("next_task_id", 0)
                print(f"从 {self.save_path} 成功加载了 {sum(len(tasks) for tasks in self.tasks.values())} 个任务")
            else:
                print(f"任务文件 {self.save_path} 不存在，使用空任务列表")
        except Exception as e:
            print(f"加载任务失败: {e}")
            # 如果加载失败，使用空任务列表
            self.tasks = {}
            self.next_task_id = 0

    def save_tasks(self):
        """保存任务到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            
            data = {
                "tasks": self.tasks,
                "next_task_id": self.next_task_id
            }
            
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"已保存 {sum(len(tasks) for tasks in self.tasks.values())} 个任务到 {self.save_path}")
        except Exception as e:
            print(f"保存任务失败: {e}")

    async def check_tasks(self):
        """检查并执行到期的任务，每10秒检查一次"""
        while self.task_running:
            now = datetime.datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            # 如果日期变更，清空已执行任务记录
            if now.day != self.last_day:
                self.executed_tasks.clear()
                self.last_day = now.day
            
            # 使用异步方式处理每个任务
            for umo, umo_tasks in self.tasks.items():
                for i, (time_str, content, task_id) in enumerate(umo_tasks):
                    try:
                        hour, minute = self.parse_time(time_str)
                        
                        # 创建任务执行标识
                        task_exec_id = f"{umo}_{task_id}_{now.day}_{hour}_{minute}"
                        
                        # 检查当前时间是否匹配且该任务今天尚未执行
                        if hour == current_hour and minute == current_minute and task_exec_id not in self.executed_tasks:
                            message = MessageChain().message(f"⏰ 定时提醒：{content}")
                            # 使用统一消息来源发送消息
                            await self.context.send_message(umo, message)
                            # 记录已执行的任务
                            self.executed_tasks.add(task_exec_id)
                    except Exception as e:
                        print(f"执行任务失败: {e}")
            
            # 等待10秒再次检查
            await asyncio.sleep(10)

    @filter.command("设置任务")
    async def set_task(self, event: AstrMessageEvent, time_str: str, content: str):
        """设置定时任务，格式为 设置任务 xx时xx分 任务内容"""
        try:
            # 验证时间格式
            self.parse_time(time_str)
            
            # 获取统一消息来源
            umo = event.unified_msg_origin
            
            # 初始化该来源的任务列表
            if umo not in self.tasks:
                self.tasks[umo] = []
            
            # 分配任务ID并添加任务
            task_id = self.next_task_id
            self.next_task_id += 1
            
            self.tasks[umo].append((time_str, content, task_id))
            
            # 保存任务到文件
            self.save_tasks()
            
            yield event.plain_result(f"✅ 已设置任务 #{task_id}：将在每天 {time_str} 提醒「{content}」")
        
        except ValueError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 设置任务失败：{str(e)}")

    @filter.command("任务列表")
    async def list_tasks(self, event: AstrMessageEvent):
        """列出当前会话的所有定时任务"""
        umo = event.unified_msg_origin
        
        if umo not in self.tasks or not self.tasks[umo]:
            yield event.plain_result("当前会话没有设置任何定时任务")
            return
        
        task_list = "\n".join([f"#{task_id}: {time_str} - {content}" for time_str, content, task_id in self.tasks[umo]])
        yield event.plain_result(f"📋 当前会话的定时任务列表：\n{task_list}")

    @filter.command("删除任务")
    async def delete_task(self, event: AstrMessageEvent, task_id: int):
        """删除指定ID的定时任务"""
        umo = event.unified_msg_origin
        
        if umo not in self.tasks:
            yield event.plain_result("当前会话没有设置任何定时任务")
            return
        
        for i, (time_str, content, tid) in enumerate(self.tasks[umo]):
            if tid == task_id:
                self.tasks[umo].pop(i)
                
                # 保存任务到文件
                self.save_tasks()
                
                yield event.plain_result(f"✅ 已删除任务 #{task_id}")
                return
        
        yield event.plain_result(f"❌ 未找到ID为 {task_id} 的任务")

    async def terminate(self):
        """插件卸载时调用"""
        # 停止任务检查循环
        self.task_running = False
        # 保存任务到文件
        self.save_tasks()
        print("定时任务插件已卸载")
