import yaml

settings_file = '/web-app-settings/config.ini'
settings = yaml.load(open(settings_file).read())
