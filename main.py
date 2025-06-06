import re
import time
import datetime
import asyncio
import threading
import json
import os
import requests
import uuid
from typing import Dict, List, Tuple, Set, Optional
from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult, MessageChain
from astrbot.api.star import Context, Star, register
import astrbot.api.message_components as Comp
from astrbot.api.message_components import At, Image

@register("timedtask", "Jason.Joestar", "一个群聊定时任务提醒插件", "1.0.0", "https://github.com/advent259141/astrbot_plugin_timedtask")
class TimedTaskPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 格式: {umo: [(time_str, content, task_id, countdown_days, start_date, target_id, image_paths), ...]}
        # 其中image_paths是本地图片路径列表
        self.tasks = {}
        self.next_task_ids = {}  # 每个群聊的下一个任务ID，格式: {umo: next_id}
        self.task_running = True
        self.executed_tasks = set()  # 记录已执行过的任务，避免重复执行
        self.last_day = datetime.datetime.now().day  # 记录上次执行的日期
        
        # 任务保存路径 - 修改为data目录下
        self.save_path = os.path.join("data", "timedtask_tasks.json")
        
        # 图片保存目录
        self.image_dir = os.path.join("data", "timedtask_images")
        os.makedirs(self.image_dir, exist_ok=True)
        
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
                    
                    # 兼容旧版本保存的数据，同时加载每个群聊的下一个任务ID
                    if "next_task_ids" in data:
                        self.next_task_ids = data.get("next_task_ids", {})
                    else:
                        # 旧版本数据，为每个群聊生成next_task_id
                        self.next_task_ids = {}
                        for umo, tasks in self.tasks.items():
                            if tasks:
                                max_id = max(task[2] for task in tasks) + 1
                                self.next_task_ids[umo] = max_id
                            else:
                                self.next_task_ids[umo] = 0
                            
                print(f"从 {self.save_path} 成功加载了 {sum(len(tasks) for tasks in self.tasks.values())} 个任务")
            else:
                print(f"任务文件 {self.save_path} 不存在，使用空任务列表")
        except Exception as e:
            print(f"加载任务失败: {e}")
            # 如果加载失败，使用空任务列表
            self.tasks = {}
            self.next_task_ids = {}

    def save_tasks(self):
        """保存任务到文件"""
        try:
            # 确保目录存在
            save_dir = os.path.dirname(self.save_path)
            os.makedirs(save_dir, exist_ok=True)
            
            data = {
                "tasks": self.tasks,
                "next_task_ids": self.next_task_ids
            }
            
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"已保存 {sum(len(tasks) for tasks in self.tasks.values())} 个任务到 {self.save_path}")
        except Exception as e:
            print(f"保存任务失败: {e}")

    def download_image(self, url: str) -> str:
        """下载图片到本地并返回本地路径"""
        # 生成唯一文件名
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(self.image_dir, filename)
        
        # 尝试多种下载方法
        methods = [
            self._download_with_session,
            self._download_with_requests,
            self._download_with_urllib,
            self._download_with_custom_ssl,
            self._download_with_simple_get,
            self._download_with_no_verify
        ]
        
        for i, method in enumerate(methods):
            try:
                print(f"尝试下载方法 {i+1}: {method.__name__}")
                if method(url, filepath):
                    print(f"图片已下载到: {filepath}")
                    return filepath
            except Exception as e:
                print(f"下载方法 {i+1} 失败: {e}")
                continue
        
        # 添加更多下载方法
        methods.append(self._download_with_simple_get)
        methods.append(self._download_with_no_verify)
        
        for i, method in enumerate(methods):
            try:
                print(f"尝试下载方法 {i+1}: {method.__name__}")
                if method(url, filepath):
                    print(f"图片已下载到: {filepath}")
                    return filepath
            except Exception as e:
                print(f"下载方法 {i+1} 失败: {e}")
                continue
        
        print(f"所有下载方法都失败了")
        return ""
    
    def _download_with_session(self, url: str, filepath: str) -> bool:
        """使用Session下载图片"""
        import ssl
        
        # 创建自定义SSL上下文
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        try:
            response = session.get(url, timeout=30, verify=False, stream=True)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return True
            else:
                print(f"Session方法状态码: {response.status_code}")
                return False
        finally:
            session.close()
    
    def _download_with_requests(self, url: str, filepath: str) -> bool:
        """使用requests直接下载"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'close',  # 强制关闭连接
            'Cache-Control': 'no-cache'
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False, stream=True)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            print(f"Requests方法状态码: {response.status_code}")
            return False
    
    def _download_with_urllib(self, url: str, filepath: str) -> bool:
        """使用urllib下载"""
        import urllib.request
        import ssl
        
        # 创建SSL上下文，忽略证书验证
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # 创建请求对象
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        req.add_header('Accept', 'image/*,*/*')
        req.add_header('Accept-Language', 'zh-CN,zh;q=0.9')
        
        # 创建HTTPS处理器
        https_handler = urllib.request.HTTPSHandler(context=ssl_context)
        opener = urllib.request.build_opener(https_handler)
        
        with opener.open(req, timeout=30) as response:
            if response.status == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.read())
                return True
            else:
                print(f"urllib方法状态码: {response.status}")
                return False
    
    def _download_with_custom_ssl(self, url: str, filepath: str) -> bool:
        """使用自定义SSL配置下载"""
        import ssl
        try:
            import urllib3
            # 禁用urllib3警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except ImportError:
            pass
        
        session = requests.Session()
        
        # 设置headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'image/avif,image/webp,*/*',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        })
        
        try:
            response = session.get(
                url, 
                timeout=30, 
                verify=False, 
                stream=True,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                return True
            else:
                print(f"自定义SSL方法状态码: {response.status_code}")
                return False
        except Exception as ssl_error:
            print(f"SSL下载方法异常: {ssl_error}")
            return False
        finally:
            session.close()
    
    def _download_with_simple_get(self, url: str, filepath: str) -> bool:
        """使用简单的GET请求下载（类似wget）"""
        response = requests.get(url, stream=True, verify=False)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            print(f"简单GET方法状态码: {response.status_code}")
            return False
    
    def _download_with_no_verify(self, url: str, filepath: str) -> bool:
        """无视SSL证书下载（不推荐，存在安全风险）"""
        response = requests.get(url, stream=True, verify=False)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            print(f"无验证下载方法状态码: {response.status_code}")
            return False

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
                        if len(task_data) >= 7:  # 包含图片路径
                            time_str, content, task_id, countdown_days, start_date, target_id, image_paths = task_data
                        elif len(task_data) >= 6:  # 包含AT信息但无图片
                            time_str, content, task_id, countdown_days, start_date, target_id = task_data
                            image_paths = []
                        elif len(task_data) >= 5:  # 包含倒计时但不包含AT和图片
                            time_str, content, task_id, countdown_days, start_date = task_data
                            target_id = None
                            image_paths = []
                        else:  # 基本任务信息
                            time_str, content, task_id = task_data
                            countdown_days = None
                            start_date = None
                            target_id = None
                            image_paths = []
                        
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
                            # 构建消息链
                            message_parts = []
                            
                            # 如果有AT目标，先添加AT组件
                            if target_id:
                                message_parts.append(Comp.At(qq=target_id))
                                message_parts.append(Comp.Plain("\n"))
                            
                            # 添加任务内容文本
                            reminder_text = "⏰ 定时提醒：\n" 
                            reminder_text += f"📝 内容：{content}\n"
                            
                            # 如果有AT目标，在文本中添加提醒对象信息
                            if target_id:
                                reminder_text += f"👤 提醒对象：{target_id}\n"
                            
                            # 如果有倒计时，添加倒计时信息
                            if countdown_days is not None and start_date is not None:
                                days_passed = (now.date() - datetime.datetime.strptime(start_date, "%Y-%m-%d").date()).days
                                days_left = countdown_days - days_passed
                                reminder_text += f"⌛ 倒计时：剩余 {days_left} 天\n"
                            
                            # 修复：确保任务ID后没有其他内容，单独成行
                            reminder_text += f"🔔 任务ID：#{task_id}"
                            
                            # 添加文本内容
                            message_parts.append(Comp.Plain(reminder_text))
                            
                            # 添加图片(如果有)，确保在新的一行
                            if image_paths:
                                message_parts.append(Comp.Plain("\n\n📷 附带图片："))
                                for img_path in image_paths:
                                    if os.path.exists(img_path):
                                        try:
                                            message_parts.append(Comp.Plain("\n"))
                                            message_parts.append(Comp.Image.fromFileSystem(img_path))
                                        except Exception as e:
                                            print(f"加载图片失败: {img_path}, 错误: {e}")
                                    else:
                                        print(f"图片文件不存在: {img_path}")
                            
                            # 创建消息链
                            message = MessageChain(message_parts)
                            
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
            
            # 初始化该来源的任务列表和next_task_id
            if umo not in self.tasks:
                self.tasks[umo] = []
            if umo not in self.next_task_ids:
                self.next_task_ids[umo] = 0
            
            # 检查是否有AT的目标和图片 - 收集所有AT和图片URL
            at_targets = []
            image_urls = []
            
            for comp in event.message_obj.message:
                if isinstance(comp, At):
                    at_targets.append(str(comp.qq))
                elif isinstance(comp, Image):
                    # 如果是图片，保存其URL
                    if hasattr(comp, 'url') and comp.url:
                        image_urls.append(comp.url)
            
            # 根据AT数量决定目标
            target_id = None
            if len(at_targets) == 1:
                # 只有一个AT，直接使用
                target_id = at_targets[0]
            elif len(at_targets) >= 2:
                # 有多个AT，假定第一个是对bot的，使用第二个
                target_id = at_targets[1]
            
            # 下载图片到本地
            image_paths = []
            for url in image_urls:
                local_path = self.download_image(url)
                if local_path:
                    image_paths.append(local_path)
            
            # 分配任务ID并添加任务
            task_id = self.next_task_ids[umo]
            self.next_task_ids[umo] += 1
            
            # 任务数据现在包括7个元素：时间、内容、任务ID、倒计时天数(None)、开始日期(None)、AT目标ID、本地图片路径
            self.tasks[umo].append((time_str, content, task_id, None, None, target_id, image_paths))
            
            # 保存任务到文件
            self.save_tasks()
            
            # 使用标准化的时间格式显示
            at_info = f"，并会AT用户 {target_id}" if target_id else ""
            img_info = f"，附带 {len(image_paths)} 张图片" if image_paths else ""
            
            yield event.plain_result(f"✅ 已设置任务 #{task_id}：将在每天 {formatted_time} 提醒「{content}」{at_info}{img_info}")
        
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
                    if len(task_data) >= 7:  # 包含图片路径
                        time_str, content, tid, _, _, target_id, image_paths = task_data
                    elif len(task_data) >= 6:  # 包含AT信息
                        time_str, content, tid, _, _, target_id = task_data
                        image_paths = []
                    else:
                        time_str, content, tid = task_data[:3]
                        target_id = None
                        image_paths = []
                    
                    # 更新任务，加入倒计时信息，保留AT信息和图片路径
                    today = datetime.datetime.now().strftime("%Y-%m-%d")
                    self.tasks[umo][i] = (time_str, content, tid, countdown_days, today, target_id, image_paths)
                    
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
            if len(task_data) >= 7:
                time_str, content, task_id, countdown_days, start_date, target_id, image_paths = task_data
                if countdown_days is not None and start_date is not None:
                    start_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    days_passed = (now.date() - start_datetime.date()).days
                    days_left = countdown_days - days_passed
                    at_info = f" (AT用户 {target_id})" if target_id else ""
                    img_info = f" (附带 {len(image_paths)} 张图片)" if image_paths else ""
                    task_list.append(f"#{task_id}: {time_str} - {content} (剩余 {days_left} 天){at_info}{img_info}")
                else:
                    at_info = f" (AT用户 {target_id})" if target_id else ""
                    img_info = f" (附带 {len(image_paths)} 张图片)" if image_paths else ""
                    task_list.append(f"#{task_id}: {time_str} - {content}{at_info}{img_info}")
            elif len(task_data) >= 6:
                time_str, content, task_id, countdown_days, start_date, target_id = task_data
                if countdown_days is not None and start_date is not None:
                    start_datetime = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    days_passed = (now.date() - start_datetime.date()).days
                    days_left = countdown_days - days_passed
                    at_info = f" (AT用户 {target_id})" if target_id else ""
                    task_list.append(f"#{task_id}: {time_str} - {content} (剩余 {days_left} 天){at_info}")
                else:
                    at_info = f" (AT用户 {target_id})" if target_id else ""
                    task_list.append(f"#{task_id}: {time_str} - {content}{at_info}")
            elif len(task_data) >= 5:
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
        """删除指定ID的定时任务，并自动重排剩余任务ID"""
        umo = event.unified_msg_origin
        
        if umo not in self.tasks:
            yield event.plain_result("当前会话没有设置任何定时任务")
            return
        
        found = False
        for i, task_data in enumerate(self.tasks[umo]):
            if len(task_data) >= 3 and task_data[2] == task_id:
                # 删除指定任务
                self.tasks[umo].pop(i)
                found = True
                break
        
        if not found:
            yield event.plain_result(f"❌ 未找到ID为 {task_id} 的任务")
            return
        
        # 自动重排剩余任务的ID
        tasks = self.tasks[umo]
        new_tasks = []
        
        # 为所有剩余任务重新分配ID
        for i, task_data in enumerate(tasks):
            if len(task_data) >= 7:  # 包含图片路径
                time_str, content, _, countdown_days, start_date, target_id, image_paths = task_data
                new_tasks.append((time_str, content, i, countdown_days, start_date, target_id, image_paths))
            elif len(task_data) >= 6:  # 包含AT信息
                time_str, content, _, countdown_days, start_date, target_id = task_data
                new_tasks.append((time_str, content, i, countdown_days, start_date, target_id, []))
            elif len(task_data) >= 5:  # 包含倒计时
                time_str, content, _, countdown_days, start_date = task_data
                new_tasks.append((time_str, content, i, countdown_days, start_date, None, []))
            else:
                time_str, content, _ = task_data[:3]
                new_tasks.append((time_str, content, i, None, None, None, []))
        
        # 更新任务列表和下一个任务ID
        self.tasks[umo] = new_tasks
        self.next_task_ids[umo] = len(new_tasks)
        
        # 保存任务到文件
        self.save_tasks()
        
        yield event.plain_result(f"✅ 已删除任务 #{task_id} 并重新排序剩余任务ID")

    @filter.command("重排任务ID")
    async def reorder_task_ids(self, event: AstrMessageEvent):
        """重新排序当前会话的所有任务ID"""
        umo = event.unified_msg_origin
        
        if umo not in self.tasks or not self.tasks[umo]:
            yield event.plain_result("当前会话没有设置任何定时任务")
            return
        
        try:
            # 获取当前任务列表
            tasks = self.tasks[umo]
            new_tasks = []
            
            # 为所有任务重新分配ID
            for i, task_data in enumerate(tasks):
                if len(task_data) >= 7:  # 包含图片路径
                    time_str, content, _, countdown_days, start_date, target_id, image_paths = task_data
                    new_tasks.append((time_str, content, i, countdown_days, start_date, target_id, image_paths))
                elif len(task_data) >= 6:  # 包含AT信息
                    time_str, content, _, countdown_days, start_date, target_id = task_data
                    new_tasks.append((time_str, content, i, countdown_days, start_date, target_id, []))
                elif len(task_data) >= 5:  # 包含倒计时
                    time_str, content, _, countdown_days, start_date = task_data
                    new_tasks.append((time_str, content, i, countdown_days, start_date, None, []))
                else:
                    time_str, content, _ = task_data[:3]
                    new_tasks.append((time_str, content, i, None, None, None, []))
            
            # 更新任务列表和下一个任务ID
            self.tasks[umo] = new_tasks
            self.next_task_ids[umo] = len(new_tasks)
            
            # 保存任务到文件
            self.save_tasks()
            
            yield event.plain_result(f"✅ 已重新排序 {len(new_tasks)} 个任务的ID")
        
        except Exception as e:
            yield event.plain_result(f"❌ 重排序任务失败：{str(e)}")

    @filter.command("timedtask_help")
    async def help_command(self, event: AstrMessageEvent):
        """显示定时任务插件的帮助信息"""
        help_text = """📅 定时任务插件使用指南 📅
        
【指令列表】
1️⃣ 设置任务 <时间> <内容>
   例如: 设置任务 8时30分 早会提醒
   例如: 设置任务 8时30分 早会提醒 @用户
   例如: 设置任务 8时30分 早会提醒 [图片]
   说明: 创建一个每天固定时间的提醒任务，可以@指定用户，也可以包含图片

2️⃣ 任务列表
   说明: 显示当前会话的所有定时任务

3️⃣ 删除任务 <任务ID>
   例如: 删除任务 1
   说明: 删除指定ID的定时任务（会自动重排序剩余任务ID）

4️⃣ 设置倒计时 <任务ID> <天数>
   例如: 设置倒计时 1 30
   说明: 为指定ID的任务设置倒计时天数，倒计时结束后任务将自动停止

5️⃣ 重排任务ID
   说明: 手动重新排序当前会话的所有任务ID，使其连续

6️⃣ timedtask_help
   说明: 显示此帮助信息

【时间格式】
时间支持以下格式:
· XX时XX分: 例如 8时30分, 12时0分
· HHMM: 例如 0830, 1200
· HH:MM: 例如 08:30, 12:00

【提示】
· 任务ID在设置任务后会自动分配，每个群聊独立编号
· 任务会在每天设定的时间提醒
· 可以在内容中@用户，提醒时会自动AT该用户
· 可以在设置任务时包含图片，提醒时会一并发送
· 倒计时任务会显示剩余天数
· 删除任务后会自动重排序剩余任务ID
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
        # 注意：不自动删除下载的图片，保留图片供下次使用
