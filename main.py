"""
公会订单管理插件 - AstrBot
功能：委托订单、查询订单、接取订单、完成订单
"""
import json
import random
from typing import Dict, List
from datetime import datetime
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path


class GuildOrdersPlugin(Star):
    """公会订单管理插件"""

    def __init__(self, context: Context):
        super().__init__(context)
        data_root = Path(get_astrbot_data_path())
        
        # 订单数据文件
        self.data_file = data_root / "plugin_data" / "guild_orders" / "guild_orders.json"
        # 计数器文件
        self.counter_file = data_root / "plugin_data" / "guild_orders" / "counter.json"
        
        self.orders: Dict[str, List[dict]] = {}
        self.counter: Dict[str, int] = {}
        
        self._load_data()
        self._load_counter()
        logger.info("公会订单插件已加载")

    def _load_data(self):
        """从文件加载订单数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.orders = json.load(f)
            except Exception as e:
                logger.error(f"加载订单数据失败: {e}")
                self.orders = {}
        else:
            self.orders = {}

    def _save_data(self):
        """保存订单数据到文件"""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.orders, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存订单数据失败: {e}")

    def _load_counter(self):
        """从文件加载计数器"""
        if self.counter_file.exists():
            try:
                with open(self.counter_file, "r", encoding="utf-8") as f:
                    self.counter = json.load(f)
            except Exception as e:
                logger.error(f"加载计数器失败: {e}")
                self.counter = {}
        else:
            self.counter = {}

    def _save_counter(self):
        """保存计数器到文件"""
        try:
            self.counter_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.counter_file, "w", encoding="utf-8") as f:
                json.dump(self.counter, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存计数器失败: {e}")

    def _get_group_orders(self, group_id: str) -> List[dict]:
        """获取指定群组的订单列表"""
        if group_id not in self.orders:
            self.orders[group_id] = []
        return self.orders[group_id]

    def _generate_order_id(self, group_id: str) -> str:
        """生成订单ID - 独立计数器持久化方案"""
        # 获取或初始化计数器
        if group_id not in self.counter:
            self.counter[group_id] = 1
        else:
            self.counter[group_id] += 1
        
        count = self.counter[group_id]
        # 保存计数器
        self._save_counter()
        
        # 格式: ORD-000001 (4位数字，支持99万+订单)
        return f"ORD-{count:04d}"

    def _get_sender_name(self, event: AstrMessageEvent) -> str:
        """获取发送者名称"""
        name = event.get_sender_name()
        if not name:
            # 尝试从 sender 中获取
            try:
                if hasattr(event.message_obj, 'sender'):
                    sender = event.message_obj.sender
                    if hasattr(sender, 'nickname'):
                        name = sender.nickname
                    elif hasattr(sender, 'card'):
                        name = sender.card
            except:
                pass
        return name or "未知玩家"

    def _order_to_text(self, order: dict) -> str:
        """将订单格式化为文本"""
        status_map = {
            "pending": "📋 待接单",
            "accepted": "🔄 进行中",
            "completed": "✅ 已完成"
        }
        status_text = status_map.get(order.get("status", "pending"), "未知状态")
        lines = [
            f"📦 **订单号**: {order['order_id']}",
            f"📝 **内容**: {order['content']}",
            f"👤 **委托人**: {order['client_name']}",
            f"📌 **状态**: {status_text}",
        ]
        if order.get("acceptor_name"):
            lines.append(f"👷 **接单人**: {order['acceptor_name']}")
        if order.get("reward"):
            lines.append(f"💰 **报酬**: {order['reward']}")
        lines.append(f"🕐 **时间**: {order['created_at']}")
        return "\n".join(lines)

    # ==================== 命令处理器 ====================
    @filter.command("帮助",alias={"help","指令","helpme","bangzhu","菜单","caidan"})
    async def cmd_帮助(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = (
            "📖 **公会订单系统 - 使用帮助**\n\n"
            "📝 **发布订单**\n"
            "`/委托 内容 报酬:xxx`\n"
            "示例：`/委托 帮我挖钻石 报酬:10钻石`\n\n"
            
            "📋 **查看订单**\n"
            "`/订单列表`\n\n"
            
            "🤝 **接取订单**\n"
            "`/接单 订单号`\n"
            "示例：`/接单 ORD-000001`\n\n"
            
            "✅ **完成订单**（仅接单人）\n"
            "`/完成 订单号`\n"
            "示例：`/完成 ORD-000001`\n\n"
            
            "✏️ **修改订单**（仅委托人）\n"
            "`/修改订单 订单号 新内容`\n"
            "示例：`/修改订单 ORD-000001 帮我挖两组钻石`\n\n"
            
            "🗑️ **删除订单**（委托人/接单人/管理员）\n"
            "`/删除订单 订单号`\n"
            "示例：`/删除订单 ORD-000001`\n\n"
            
            "💡 **提示**\n"
            "• 订单号从 `/订单列表` 中获取\n"
            "• 委托人不可以接自己的订单\n"
            "• 所有命令在群聊中使用"
        )
        yield event.plain_result(help_text)

    @filter.command("委托",alias={"发布订单","weituo"})
    async def cmd_委托(self, event: AstrMessageEvent):
        """委托订单"""
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("❌ 该功能仅支持群聊")
            return

        message = event.message_str.strip()
        parts = message.split(" ", 1)
        if len(parts) < 2:
            yield event.plain_result(
                "❌ 用法: `/委托 订单内容 [报酬:xxx]`\n"
                "示例: `/委托 帮我挖一组钻石 报酬:10钻石`"
            )
            return

        raw_content = parts[1]
        reward = ""
        content = raw_content
        if "报酬:" in raw_content:
            split_idx = raw_content.find("报酬:") + len("报酬:")
            content = raw_content[:split_idx].strip()
            reward = raw_content[split_idx:].strip()
        elif "报酬：" in raw_content:
            split_idx = raw_content.find("报酬：")+len("报酬：")
            content = raw_content[:split_idx].strip()
            reward = raw_content[split_idx:].strip()
        elif "报酬" in raw_content:
            split_idx = raw_content.find("报酬")+len("报酬")
            content = raw_content[:split_idx].strip()
            reward = raw_content[split_idx:].strip()

        if not content:
            yield event.plain_result("❌ 订单内容不能为空")
            return

        # 获取发送者信息
        sender_name = self._get_sender_name(event)
        sender_id = event.get_sender_id()

        order_id = self._generate_order_id(group_id)

        order = {
            "order_id": order_id,
            "content": content,
            "client_id": sender_id,
            "client_name": sender_name,
            "reward": reward,
            "status": "pending",
            "acceptor_id": None,
            "acceptor_name": None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": None
        }

        group_orders = self._get_group_orders(group_id)
        group_orders.append(order)
        self._save_data()

        yield event.plain_result(
            f"✅ 订单已创建！\n\n{self._order_to_text(order)}\n\n"
            f"💡 其他成员可使用 `/接单 {order['order_id']}` 接取此订单"
        )

    @filter.command("订单列表",alias={"dingdanliebiao","dingdan","订单","列表"})
    async def cmd_订单列表(self, event: AstrMessageEvent):
        """查询当前所有待接单和进行中的订单"""
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("❌ 该功能仅支持群聊")
            return

        group_orders = self._get_group_orders(group_id)
        pending = [o for o in group_orders if o.get("status") == "pending"]
        accepted = [o for o in group_orders if o.get("status") == "accepted"]

        if not pending and not accepted:
            yield event.plain_result("📭 当前没有进行中的订单")
            return

        lines = []
        if pending:
            lines.append(f"📋 **待接单 ({len(pending)})**:")
            for o in pending:
                lines.append(f"  • `{o['order_id']}` {o['content']}")
                lines.append(f"    👤 委托人: {o['client_name']}")
                if o.get('reward'):
                    lines.append(f"    💰 报酬: {o['reward']}")
                lines.append("")  # 空行分隔
        
        if accepted:
            lines.append(f"🔄 **进行中 ({len(accepted)})**:")
            for o in accepted:
                lines.append(f"  • `{o['order_id']}` {o['content']}")
                lines.append(f"    👤 委托人: {o['client_name']}")
                lines.append(f"    👷 接单人: {o.get('acceptor_name', '未知')}")
                if o.get('reward'):
                    lines.append(f"    💰 报酬: {o['reward']}")
                lines.append("")  # 空行分隔

        lines.append("💡 使用 `/接单 [订单号]` 接取订单")
        yield event.plain_result("\n".join(lines))

    @filter.command("接单",alias={"jiedan","接受委托","jieshouweituo"})
    async def cmd_接单(self, event: AstrMessageEvent):
        """接取订单"""
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("❌ 该功能仅支持群聊")
            return

        parts = event.message_str.strip().split(" ", 1)
        if len(parts) < 2:
            yield event.plain_result("❌ 请指定订单号\n用法: `/接单 [订单号]`")
            return

        order_id = parts[1].strip().upper().upper()
        group_orders = self._get_group_orders(group_id)

        target_order = None
        for o in group_orders:
            if o["order_id"].upper() == order_id:
                target_order = o
                break

        if not target_order:
            yield event.plain_result(f"❌ 未找到订单 `{order_id}`，请检查订单号")
            return

        if target_order["status"] != "pending":
            yield event.plain_result(f"❌ 订单 `{order_id}` 已被接取或已完成，当前状态: {target_order['status']}")
            return

        if target_order["client_id"] == event.get_sender_id():
            yield event.plain_result("❌ 你不能接取自己委托的订单")
            return

        # 获取接单人信息
        acceptor_name = self._get_sender_name(event)
        acceptor_id = event.get_sender_id()

        target_order["status"] = "accepted"
        target_order["acceptor_id"] = acceptor_id
        target_order["acceptor_name"] = acceptor_name
        self._save_data()

        yield event.plain_result(
            f"✅ {acceptor_name} 已接取订单！\n\n"
            f"{self._order_to_text(target_order)}\n\n"
            f"💡 完成后请使用 `/完成 {order_id}` 关闭订单"
        )

    @filter.command("完成",alias={"wancheng","结单"})
    async def cmd_完成(self, event: AstrMessageEvent):
        """完成订单"""
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("❌ 该功能仅支持群聊")
            return

        parts = event.message_str.strip().split(" ", 1)
        if len(parts) < 2:
            yield event.plain_result("❌ 请指定订单号\n用法: `/完成 [订单号]`")
            return

        order_id = parts[1].strip().upper().upper()
        group_orders = self._get_group_orders(group_id)

        target_order = None
        for o in group_orders:
            if o["order_id"].upper() == order_id:
                target_order = o
                break

        if not target_order:
            yield event.plain_result(f"❌ 未找到订单 `{order_id}`")
            return

        if target_order["status"] == "pending":
            yield event.plain_result(f"❌ 订单 `{order_id}` 尚未被接取，请先接单")
            return

        if target_order["status"] == "completed":
            yield event.plain_result(f"❌ 订单 `{order_id}` 已完成")
            return

        if target_order["acceptor_id"] != event.get_sender_id():
            yield event.plain_result(f"❌ 只有接单人 `{target_order.get('acceptor_name')}` 可以完成此订单")
            return

        target_order["status"] = "completed"
        target_order["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_data()

        yield event.plain_result(
            f"🎉 订单已完成！\n\n{self._order_to_text(target_order)}\n\n"
            f"💡 如需清理，可使用 `/删除订单 {order_id}` 从列表中移除"
        )

    @filter.command("修改订单",alias={"修改","xiugai","xiugaidingdan"})
    async def cmd_修改订单(self, event: AstrMessageEvent):
        """
        修改订单内容（仅委托人）
        用法: /修改订单 [订单号] [新内容] [新报酬(可选)]
        示例: /修改订单 ORD-000001 帮我挖两组钻石 报酬:20钻石
        """
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("❌ 该功能仅支持群聊")
            return

        parts = event.message_str.strip().split(" ", 2)  # 最多分割成3部分
        if len(parts) < 3:
            yield event.plain_result(
                "❌ 用法: `/修改订单 [订单号] [新内容] [新报酬:xxx]`\n"
                "示例: `/修改订单 ORD-000001 帮我挖两组钻石 报酬:20钻石`"
            )
            return

        order_id = parts[1].strip().upper()
        raw_content = parts[2].strip()

        # 提取报酬（如果有）
        reward = ""
        content = raw_content
        if "报酬:" in raw_content:
            split_idx = raw_content.find("报酬:")
            content = raw_content[:split_idx].strip()
            reward = raw_content[split_idx:].strip()
        elif "报酬：" in raw_content:
            split_idx = raw_content.find("报酬：")
            content = raw_content[:split_idx].strip()
            reward = raw_content[split_idx:].strip()

        if not content:
            yield event.plain_result("❌ 订单内容不能为空")
            return

        group_orders = self._get_group_orders(group_id)

        # 查找订单
        target_order = None
        target_idx = None
        for idx, o in enumerate(group_orders):
            if o["order_id"].upper() == order_id:
                target_idx = idx
                target_order = o
                break

        if not target_order:
            yield event.plain_result(f"❌ 未找到订单 `{order_id}`，请检查订单号")
            return

        # 权限检查：只有委托人可以修改
        if target_order["client_id"] != event.get_sender_id():
            yield event.plain_result(f"❌ 只有委托人 `{target_order['client_name']}` 可以修改此订单")
            return

        # 状态检查：只有待接单和进行中可以修改
        if target_order["status"] == "completed":
            yield event.plain_result(f"❌ 订单 `{order_id}` 已完成，无法修改")
            return

        # 保存旧内容用于提示
        old_content = target_order["content"]
        old_reward = target_order.get("reward", "无")

        # 修改订单
        target_order["content"] = content
        if reward:
            target_order["reward"] = reward

        self._save_data()

        yield event.plain_result(
            f"✅ 订单已修改！\n\n"
            f"📦 **订单号**: {order_id}\n"
            f"📝 **原内容**: {old_content}\n"
            f"📝 **新内容**: {content}\n"
            f"💰 **原报酬**: {old_reward}\n"
            f"💰 **新报酬**: {target_order.get('reward', '无')}\n\n"
            f"📌 **当前状态**: {self._order_to_text(target_order)}"
        )
    @filter.command("放弃订单",alias={"放弃","fangqi","fangqidingdan"})
    async def cmd_放弃订单(self, event: AstrMessageEvent):
        """
        放弃已接取的订单（仅接单人）
        用法: /放弃订单 [订单号]
        示例: /放弃订单 ORD-0001
        """
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("❌ 该功能仅支持群聊")
            return

        parts = event.message_str.strip().split(" ", 1)
        if len(parts) < 2:
            yield event.plain_result("❌ 请指定订单号\n用法: `/放弃订单 [订单号]`")
            return

        order_id = parts[1].strip().upper()
        group_orders = self._get_group_orders(group_id)

        # 查找订单
        target_order = None
        for o in group_orders:
            if o["order_id"].upper() == order_id:
                target_order = o
                break

        if not target_order:
            yield event.plain_result(f"❌ 未找到订单 `{order_id}`，请检查订单号")
            return

        # 状态检查：只有进行中的订单可以放弃
        if target_order["status"] == "pending":
            yield event.plain_result(f"❌ 订单 `{order_id}` 尚未被接取，无需放弃")
            return

        if target_order["status"] == "completed":
            yield event.plain_result(f"❌ 订单 `{order_id}` 已完成，无法放弃")
            return

        # 权限检查：只有接单人本人可以放弃
        if target_order["acceptor_id"] != event.get_sender_id():
            yield event.plain_result(f"❌ 只有接单人 `{target_order.get('acceptor_name')}` 可以放弃此订单")
            return

        # 保存接单人信息用于提示
        acceptor_name = target_order.get("acceptor_name", "未知")

        # 放弃订单：清空接单人信息，状态改为待接单
        target_order["status"] = "pending"
        target_order["acceptor_id"] = None
        target_order["acceptor_name"] = None
        self._save_data()

        yield event.plain_result(
            f"✅ {acceptor_name} 已放弃订单 `{order_id}`！\n\n"
            f"📦 **订单号**: {order_id}\n"
            f"📝 **内容**: {target_order['content']}\n"
            f"👤 **委托人**: {target_order['client_name']}\n"
            f"📌 **状态**: 📋 待接单\n"
            f"💰 **报酬**: {target_order.get('reward', '无')}\n\n"
            f"💡 该订单已重新回到待接单列表，其他成员可再次接取"
        )
    @filter.command("删除订单",alias={"删除","shanchu","shanchudingdan"})
    async def cmd_删除订单(self, event: AstrMessageEvent):
        """删除订单"""
        group_id = event.message_obj.group_id
        if not group_id:
            yield event.plain_result("❌ 该功能仅支持群聊")
            return

        parts = event.message_str.strip().split(" ", 1)
        if len(parts) < 2:
            yield event.plain_result("❌ 请指定订单号\n用法: `/删除订单 [订单号]`")
            return

        order_id = parts[1].strip().upper()
        group_orders = self._get_group_orders(group_id)

        target_idx = None
        target_order = None
        for idx, o in enumerate(group_orders):
            if o["order_id"].upper() == order_id:
                target_idx = idx
                target_order = o
                break

        if target_idx is None:
            yield event.plain_result(f"❌ 未找到订单 `{order_id}`")
            return

        # 权限检查
        is_client = target_order["client_id"] == event.get_sender_id()
        is_acceptor = target_order.get("acceptor_id") == event.get_sender_id()

        try:
            is_admin = event.is_admin() if hasattr(event, "is_admin") else False
        except:
            is_admin = False

        if not (is_admin or is_client or is_acceptor):
            yield event.plain_result("❌ 只有委托人、接单人或群管理员可以删除此订单")
            return

        del group_orders[target_idx]
        self._save_data()
        yield event.plain_result(f"✅ 已删除订单 `{order_id}`")

    async def terminate(self):
        """插件卸载时调用"""
        self._save_data()
        self._save_counter()
        logger.info("公会订单插件已卸载")