import logging

logging.addLevelName(logging.WARNING+1, "WAKEUP")
logging.WAKEUP = logging.WARNING+1
logging.addLevelName(logging.WARNING+2, "LIGHTS")
logging.LIGHTS = logging.WARNING+2
