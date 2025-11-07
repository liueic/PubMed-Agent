"""
统一日志配置模块
提供彩色终端输出、文件日志支持和不同级别的日志格式化
"""

import logging
import sys
import os
from typing import Optional
from logging.handlers import RotatingFileHandler


# ANSI颜色代码（不依赖colorama）
class Colors:
    """ANSI颜色代码"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # 前景色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 亮色
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    # 日志级别对应的颜色
    LEVEL_COLORS = {
        'DEBUG': Colors.BRIGHT_BLACK,
        'INFO': Colors.BRIGHT_CYAN,
        'WARNING': Colors.BRIGHT_YELLOW,
        'ERROR': Colors.BRIGHT_RED,
        'CRITICAL': Colors.BRIGHT_RED + Colors.BOLD,
    }
    
    # 模块名颜色
    MODULE_COLOR = Colors.BRIGHT_BLUE
    
    def __init__(self, use_color: bool = True, detailed: bool = False):
        """
        初始化彩色格式化器
        
        Args:
            use_color: 是否使用颜色
            detailed: 是否显示详细信息（时间戳、函数名等）
        """
        self.use_color = use_color and self._is_terminal()
        self.detailed = detailed
        
        if detailed:
            fmt = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        else:
            fmt = '[%(levelname)s] [%(name)s] %(message)s'
        
        super().__init__(fmt=fmt, datefmt='%Y-%m-%d %H:%M:%S')
    
    def _is_terminal(self) -> bool:
        """检查是否在终端中运行"""
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        if self.use_color:
            # 保存原始级别名
            original_levelname = record.levelname
            
            # 添加颜色
            level_color = self.LEVEL_COLORS.get(original_levelname, Colors.RESET)
            record.levelname = f"{level_color}{original_levelname}{Colors.RESET}"
            
            # 模块名颜色
            if self.detailed:
                record.name = f"{self.MODULE_COLOR}{record.name}{Colors.RESET}"
            else:
                # 简化模块名（只显示最后一部分）
                module_name = record.name.split('.')[-1]
                record.name = f"{self.MODULE_COLOR}{module_name}{Colors.RESET}"
        
        return super().format(record)


class SimpleFormatter(logging.Formatter):
    """简单格式化器（用于文件日志）"""
    
    def __init__(self, detailed: bool = True):
        """
        初始化简单格式化器
        
        Args:
            detailed: 是否显示详细信息
        """
        if detailed:
            fmt = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        else:
            fmt = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        
        super().__init__(fmt=fmt, datefmt='%Y-%m-%d %H:%M:%S')


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    detailed: bool = False,
    use_color: bool = True
) -> None:
    """
    设置统一的日志配置
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为None则不写入文件
        detailed: 是否显示详细信息（时间戳、函数名等）
        use_color: 是否使用彩色输出（仅控制台）
    """
    # 转换日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # 清除现有的处理器（避免重复添加）
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = ColoredFormatter(use_color=use_color, detailed=detailed)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 使用RotatingFileHandler支持日志轮转
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_formatter = SimpleFormatter(detailed=True)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别（避免过多输出）
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('langchain').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称（通常是模块名）
        
    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)

