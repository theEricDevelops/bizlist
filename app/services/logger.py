import logging
import os
from logging.handlers import RotatingFileHandler

class Logger:
    """
    A custom logger that writes to a file and optionally to console.
    """
    def __init__(self, name, log_file=None, log_level=logging.DEBUG, log_format=None, console_log=True):
        """
        Initialize a new logger.
        
        Args:
            name (str): Logger name, typically __name__ of the calling module
            log_file (str, optional): Log file name. Defaults to {name}.log
            log_level (int, optional): Logging level. Defaults to DEBUG.
            console_log (bool, optional): Whether to log to console. Defaults to True.
        """
        self.name = name
        self.log_file = log_file if log_file else f"{name}.log"
        self.log_level = log_level
        self.console_log = console_log
        self.log_format = log_format if log_format else '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.logger.propagate = False
        
        # Clear existing handlers to prevent duplicates when reusing the logger
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Set up file handler
        file_path = os.path.join(logs_dir, self.log_file)
        file_handler = RotatingFileHandler(file_path, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(self.log_format)
        file_handler.setFormatter(formatter)
        
        # Add file handler to logger
        self.logger.addHandler(file_handler)
        
        # Set up console handler if requested
        if console_log:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def debug(self, message):
        """Log a debug message."""
        self.logger.debug(message)
    
    def info(self, message):
        """Log an info message."""
        self.logger.info(message)
    
    def warning(self, message):
        """Log a warning message."""
        self.logger.warning(message)
    
    def error(self, message):
        """Log an error message."""
        self.logger.error(message)
    
    def critical(self, message):
        """Log a critical message."""
        self.logger.critical(message)
