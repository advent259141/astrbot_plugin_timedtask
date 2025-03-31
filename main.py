import re
import time
import datetime
import asyncio
import threading
import json
import os
from typing import Dict, List, Tuple, Set, Optional

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.event import MessageChain

@register("timedtask", "astrbot", "一个群聊定时任务提醒插件", "1.0.0", "https://github.com/yourusername/astrbot_plugin_timedtask")
class TimedTaskPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.tasks = {}  # 格式: {umo: [(time_str, content, task_id, countdown_days, start_date), ...]}
        self.next_task_id = 0
        self.task_running = True
        self.executed_tasks = set()  # 记录已执行过的任务，避免重复执行
        self.last_day = datetime.datetime.now().day  # 记录上次执行的日期
        
        # 任务保存路径 - 修改为data目录下
        self.save_path = os.path.join("data", "timedtask_tasks.json")
        
        # 加载保存的任务
        self.load_tasks()
        
        # 异步启动任务检查器
        asyncio.create_task(self.check_tasks())
        print("定时任务插件已加载")

    def parse_time(self, time_str: str) -> Tuple[int, int]:
        """解析时间字符串，支持多种格式
        
        支持的格式:
        - XX时XX分: 例如 "8时30分"
        - HHMM: 例如 "0830"
        - HH:MM: 例如 "08:30"
        """
        # 尝试匹配 "XX时XX分" 格式
        pattern1 = r'(\d+)时(\d+)分'
        match = re.match(pattern1, time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError("时间范围错误，小时应在0-23之间，分钟应在0-59之间")
            
            return hour, minute
        
        # 尝试匹配 "HH:MM" 格式
        pattern2 = r'(\d{1,2}):(\d{2})'
        match = re.match(pattern2, time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError("时间范围错误，小时应在0-23之间，分钟应在0-59之间")
            
            return hour, minute
        
        # 尝试匹配 "HHMM" 格式
        pattern3 = r'^(\d{2})(\d{2})$'
        match = re.match(pattern3, time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError("时间范围错误，小时应在0-23之间，分钟应在0-59之间")
            
            return hour, minute
        
        # 如果所有格式都不匹配，则抛出错误
        raise ValueError("时间格式错误，支持的格式有：XX时XX分、HHMM、HH:MM")

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
            save_dir = os.path.dirname(self.save_path)
            os.makedirs(save_dir, exist_ok=True)
            
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
            current_date = now.strftime("%Y-%m-%d")
            
            # 如果日期变更，清空已执行任务记录
            if now.day != self.last_day:
                self.executed_tasks.clear()
                self.last_day = now.day
            
            # 使用异步方式处理每个任务
            for umo, umo_tasks in list(self.tasks.items()):  # 使用list创建副本，避免修改字典时报错
                for i, task_data in enumerate(list(umo_tasks)):  # 同样使用副本
                    try:
                        # 解构任务数据，适应不同长度的元组
                        if len(task_data) >= 5:
                            time_str, content, task_id, countdown_days, start_date = task_data
                        else:
                            time_str, content, task_id = task_data
                            countdown_days = None
                            start_date = None
                        
                        # 检查倒计时是否已结束
                        if countdown_days is not None and start_date is not None:
                            start_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                            days_passed = (now.date() - start_datetime.date()).days
                            days_left = countdown_days - days_passed
                            
                            # 如果倒计时结束，移除任务并继续下一个
                            if days_left <= 0:
                                umo_tasks.pop(i)
                                self.save_tasks()
                                continue
                        
                        hour, minute = self.parse_time(time_str)
                        
                        # 创建任务执行标识
                        task_exec_id = f"{umo}_{task_id}_{now.day}_{hour}_{minute}"
                        
                        # 检查当前时间是否匹配且该任务今天尚未执行
                        if hour == current_hour and minute == current_minute and task_exec_id not in self.executed_tasks:
                            # 根据是否有倒计时生成不同的消息
                            if countdown_days is not None and start_date is not None:
                                days_passed = (now.date() - datetime.datetime.strptime(start_date, "%Y-%m-%d").date()).days
                                days_left = countdown_days - days_passed
                                message = MessageChain().message(f"⏰ 定时提醒：\n{content}\n(剩余 {days_left} 天)")
                            else:
                                message = MessageChain().message(f"⏰ 定时提醒：\n{content}")
                            
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
            # 验证时间格式并获取小时和分钟
            hour, minute = self.parse_time(time_str)
            
            # 创建标准化的时间显示格式
            formatted_time = f"{hour}时{minute}分"
            
            # 获取统一消息来源
            umo = event.unified_msg_origin
            
            # 初始化该来源的任务列表
            if umo not in self.tasks:
                self.tasks[umo] = []
            
            # 分配任务ID并添加任务
            task_id = self.next_task_id
            self.next_task_id += 1
            
            # 任务数据现在包括5个元素：时间、内容、任务ID、倒计时天数(None)、开始日期(None)
            self.tasks[umo].append((time_str, content, task_id, None, None))
            
            # 保存任务到文件
            self.save_tasks()
            
            # 使用标准化的时间格式显示
            yield event.plain_result(f"✅ 已设置任务 #{task_id}：将在每天 {formatted_time} 提醒「{content}」")
        
        except ValueError as e:
            yield event.plain_result(f"❌ {str(e)}")
        except Exception as e:
            yield event.plain_result(f"❌ 设置任务失败：{str(e)}")

    @filter.command("设置倒计时")
    async def set_task_countdown(self, event: AstrMessageEvent, task_id: int, countdown_days: int):
        """设置任务倒计时，格式为 设置倒计时 任务ID 天数"""
        try:
            if countdown_days <= 0:
                yield event.plain_result("❌ 倒计时天数必须大于0")
                return
            
            umo = event.unified_msg_origin
            
            if umo not in self.tasks:
                yield event.plain_result("❌ 当前会话没有设置任何定时任务")
                return
            
            found = False
            for i, task_data in enumerate(self.tasks[umo]):
                if len(task_data) >= 3 and task_data[2] == task_id:
                    # 获取现有的任务数据
                    time_str, content, tid = task_data[:3]
                    
                    # 更新任务，加入倒计时信息
                    today = datetime.datetime.now().strftime("%Y-%m-%d")
                    self.tasks[umo][i] = (time_str, content, tid, countdown_days, today)
                    
                    self.save_tasks()
                    yield event.plain_result(f"✅ 已为任务 #{task_id} 设置 {countdown_days} 天倒计时")
                    found = True
                    break
            
            if not found:
                yield event.plain_result(f"❌ 未找到ID为 {task_id} 的任务")
        
        except Exception as e:
            yield event.plain_result(f"❌ 设置倒计时失败：{str(e)}")

    @filter.command("任务列表")
    async def list_tasks(self, event: AstrMessageEvent):
        """列出当前会话的所有定时任务"""
        umo = event.unified_msg_origin
        
        if umo not in self.tasks or not self.tasks[umo]:
            yield event.plain_result("当前会话没有设置任何定时任务")
            return
        
        task_list = []
        now = datetime.datetime.now()
        
        for task_data in self.tasks[umo]:
            if len(task_data) >= 5:
                time_str, content, task_id, countdown_days, start_date = task_data
                if countdown_days is not None and start_date is not None:
                    start_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    days_passed = (now.date() - start_datetime.date()).days
                    days_left = countdown_days - days_passed
                    task_list.append(f"#{task_id}: {time_str} - {content} (剩余 {days_left} 天)")
                else:
                    task_list.append(f"#{task_id}: {time_str} - {content}")
            else:
                time_str, content, task_id = task_data[:3]
                task_list.append(f"#{task_id}: {time_str} - {content}")
        
        yield event.plain_result(f"📋 当前会话的定时任务列表：\n" + "\n".join(task_list))

    @filter.command("删除任务")
    async def delete_task(self, event: AstrMessageEvent, task_id: int):
        """删除指定ID的定时任务"""
        umo = event.unified_msg_origin
        
        if umo not in self.tasks:
            yield event.plain_result("当前会话没有设置任何定时任务")
            return
        
        for i, (time_str, content, tid, *_) in enumerate(self.tasks[umo]):
            if tid == task_id:
                self.tasks[umo].pop(i)
                
                # 保存任务到文件
                self.save_tasks()
                
                yield event.plain_result(f"✅ 已删除任务 #{task_id}")
                return
        
        yield event.plain_result(f"❌ 未找到ID为 {task_id} 的任务")

    @filter.command("timedtask_help")
    async def help_command(self, event: AstrMessageEvent):
        """显示定时任务插件的帮助信息"""
        help_text = """📅 定时任务插件使用指南 📅
        
【指令列表】
1️⃣ 设置任务 <时间> <内容>
   例如: 设置任务 8时30分 早会提醒
   例如: 设置任务 0830 早会提醒
   例如: 设置任务 08:30 早会提醒
   说明: 创建一个每天固定时间的提醒任务

2️⃣ 任务列表
   说明: 显示当前会话的所有定时任务

3️⃣ 删除任务 <任务ID>
   例如: 删除任务 1
   说明: 删除指定ID的定时任务

4️⃣ 设置倒计时 <任务ID> <天数>
   例如: 设置倒计时 1 30
   说明: 为指定ID的任务设置倒计时天数，倒计时结束后任务将自动停止

5️⃣ timedtask_help
   说明: 显示此帮助信息

【时间格式】
时间支持以下格式:
· XX时XX分: 例如 8时30分, 12时0分
· HHMM: 例如 0830, 1200
· HH:MM: 例如 08:30, 12:00

【提示】
· 任务ID在设置任务后会自动分配
· 任务会在每天设定的时间提醒
· 倒计时任务会显示剩余天数
· 插件重启后任务不会丢失
"""
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件卸载时调用"""
        # 停止任务检查循环
        self.task_running = False
        # 保存任务到文件
        self.save_tasks()
        print("定时任务插件已卸载")
