import logging.config
from pkg_resources import resource_filename

class LoggerFactory:
    DEFALUT_LOG_CONFIG="logging.conf"

    @classmethod
    def create_logger(cls, instance):
        if isinstance(instance, str):
            return logging.getLogger(instance)
        else:
            return logging.getLogger("%s.%s" % ( instance.__module__, instance.__class__.__name__))

    @classmethod
    def init(cls, config_file=None):
        if config_file is None:
            config_path = resource_filename(__name__, LoggerFactory.DEFALUT_LOG_CONFIG)
        else:
            config_path = resource_filename(__name__, config_file)

        with open(config_path) as config:
            logging.config.fileConfig(config)
