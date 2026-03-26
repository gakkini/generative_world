"""时间系统"""


class TimeSystem:
    """通用的时间追踪系统"""
    
    def __init__(self, config=None):
        self.day = 1
        self.month = 1
        self.year = 1
        self.days_per_year = config.get('days_per_year', 360) if config else 360
        
    def advance(self, days=1):
        """推进时间"""
        self.day += days
        while self.day > self.days_per_year:
            self.day -= self.days_per_year
            self.year += 1
            self.month = 1
        
    def get_time_str(self) -> str:
        """获取当前时间字符串"""
        return f"第{self.day}日"
    
    def get_full_time_str(self) -> str:
        """获取完整时间字符串"""
        return f"修仙纪元{self.year}年 第{self.day}日"
    
    def to_dict(self):
        return {
            'day': self.day,
            'month': self.month,
            'year': self.year
        }
