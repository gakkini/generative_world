"""剧本引擎：处理主线剧情触发"""
import yaml


class PlotNode:
    """剧本节点"""
    
    def __init__(self, node_id, config):
        self.id = node_id
        self.title = config.get('title', '')
        self.description = config.get('description', '')
        self.trigger = config.get('trigger', {})
        self.actions = config.get('actions', [])
        self.consequences = config.get('consequences', [])
        self.completed = False
    
    def check_trigger(self, world_state, agents) -> bool:
        """检查是否满足触发条件"""
        if self.completed:
            return False
        
        trigger = self.trigger
        trigger_type = trigger.get('type', 'always')
        
        if trigger_type == 'always':
            return True
        elif trigger_type == 'day':
            return world_state.get('day', 0) >= trigger.get('value', 1)
        elif trigger_type == 'location':
            char_id = trigger.get('character')
            loc = trigger.get('location')
            return world_state.get('positions', {}).get(char_id) == loc
        elif trigger_type == 'relationship':
            # 检查角色关系达到阈值
            char_a = trigger.get('character_a')
            char_b = trigger.get('character_b')
            threshold = trigger.get('threshold', 50)
            # TODO: 接入关系系统
            return False
        elif trigger_type == 'composite':
            # AND/OR 组合条件
            operator = trigger.get('operator', 'and')
            conditions = trigger.get('conditions', [])
            
            results = []
            for cond in conditions:
                # 递归检查每个子条件
                sub_node = PlotNode(f"sub_{self.id}", {'trigger': cond})
                results.append(sub_node.check_trigger(world_state, agents))
            
            if operator == 'and':
                return all(results)
            else:
                return any(results)
        
        return False


class PlotEngine:
    """剧本引擎"""
    
    def __init__(self, world):
        self.world = world
        self.nodes = {}  # node_id -> PlotNode
        self.active_nodes = []  # 当前激活的节点
        self.completed_nodes = []  # 已完成的节点
        self.triggered_events = []  # 已触发的事件记录
    
    def load_plot(self, yaml_path):
        """从YAML加载剧本"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            plot_data = yaml.safe_load(f)
        
        for node_id, config in plot_data.get('nodes', {}).items():
            self.nodes[node_id] = PlotNode(node_id, config)
    
    def add_node(self, node_id, config):
        """运行时动态添加剧本节点"""
        self.nodes[node_id] = PlotNode(node_id, config)
    
    def update_node(self, node_id, changes):
        """运行时修改剧本节点"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            for key, value in changes.items():
                if hasattr(node, key):
                    setattr(node, key, value)
    
    def check_triggers(self, agents):
        """检查所有节点的触发条件"""
        world_state = self.world.get_state_summary()
        
        for node_id, node in self.nodes.items():
            if node_id in self.completed_nodes:
                continue
            
            if node.check_trigger(world_state, agents):
                self._activate_node(node)
    
    def _activate_node(self, node):
        """激活并执行剧本节点"""
        print(f"\n🔔 [剧本触发] {node.title}")
        
        # 执行动作
        for action in node.actions:
            self._execute_action(action)
        
        # 记录后果
        for consequence in node.consequences:
            self._apply_consequence(consequence)
        
        node.completed = True
        self.completed_nodes.append(node.id)
        self.active_nodes.append(node.id)
    
    def _execute_action(self, action):
        """执行剧本动作"""
        action_type = action.get('type')
        
        if action_type == 'force_event':
            # 强制事件：分发给指定角色
            target_id = action.get('target_id')
            event_content = action.get('content', '')
            # 通知角色感知这个事件
            print(f"   📢 {target_id} 收到消息：{event_content}")
            
        elif action_type == 'move_character':
            # 移动角色
            char_id = action.get('character_id')
            dest = action.get('destination')
            days = self.world.move_character(char_id, dest)
            print(f"   🚀 {char_id} 移动到 {dest}（耗时{days}日）")
            
        elif action_type == 'send_message':
            # 发送消息
            from_id = action.get('from')
            to_id = action.get('to')
            content = action.get('content', '')
            print(f"   💬 {from_id} 对 {to_id} 说：{content}")
    
    def _apply_consequence(self, consequence):
        """应用剧本后果"""
        cons_type = consequence.get('type')
        
        if cons_type == 'unlock_plot':
            # 解锁新剧本
            new_node_id = consequence.get('plot_id')
            print(f"   🔓 解锁新剧情：{new_node_id}")
            
        elif cons_type == 'modify_state':
            # 修改世界状态
            key = consequence.get('key')
            value = consequence.get('value')
            print(f"   ⚙️ 世界状态变更：{key} = {value}")
    
    def get_status(self) -> dict:
        """获取剧本状态"""
        return {
            'total_nodes': len(self.nodes),
            'completed': len(self.completed_nodes),
            'active': len(self.active_nodes),
            'pending': len(self.nodes) - len(self.completed_nodes)
        }
