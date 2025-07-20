import logging
import sys

def setup_logging():
    """
    Configures logging for the application.
    
    - Logs to standard output.
    - Uses a format that includes timestamp, log level, and message.
    - Sets the default logging level to INFO.
    - Integrates with Google Cloud Logging if the library is available.
    """
    # Attempt to use Google Cloud Logging handler if available
    try:
        from google.cloud.logging.handlers import CloudLoggingHandler
        import google.cloud.logging
        
        client = google.cloud.logging.Client()
        handler = CloudLoggingHandler(client)
        
        # The Cloud Logging handler already includes severity and timestamp
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        print("✅ Successfully configured Google Cloud Logging.")
        
    except ImportError:
        print("⚠️ Google Cloud Logging library not found. Falling back to standard console logging.")
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

    # Get the root logger and configure it
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers and add the new one
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy loggers from libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    logging.getLogger('google.api_core').setLevel(logging.WARNING)

# Call setup function immediately so logging is configured on import
setup_logging()
