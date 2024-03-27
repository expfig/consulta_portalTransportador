import logging
import logging_loki
from decouple import config


def get_logger(name: str) -> logging.Logger:
    handler = logging_loki.LokiHandler(
        url=config("log_server_url", default="http://10.0.0.72:3100/loki/api/v1/push"),
        version="1",
    )
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


if __name__ == "__main__":
    logger = get_logger("testes")
    logger.info("Hello World!")
    logger.debug("debug")
    logger.error("error")
