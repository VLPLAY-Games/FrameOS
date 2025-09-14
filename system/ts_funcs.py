import modules.logger as logger

# Callback функции для 
def ts_handle_touch():
    logger.info("Short touch detected")
    # Действие при коротком касании

def ts_handle_long_press():
    logger.info("Long press detected") 
    # Действие при длительном нажатии

def ts_handle_double_tap():
    logger.info("Double tap detected")
    # Действие при двойном нажатии