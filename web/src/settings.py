import yaml

settings_file = '/web-app-settings/config.ini'
settings = yaml.load(open(settings_file).read())

logging_file = '/web-app-settings/logging.ini'
logging_settings = yaml.load(open(logging_file).read())