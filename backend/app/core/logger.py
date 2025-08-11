import logging

def setup_logger(name: str):
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger
