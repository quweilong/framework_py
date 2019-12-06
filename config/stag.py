# -*- coding: utf-8 -*-
from config import RUN_VER
if RUN_VER == 'open':
    from blueapps.patch.settings_open_saas import *  # noqa
else:
    from blueapps.patch.settings_paas_services import  * # noqa

# 预发布环境
RUN_MODE = 'STAGING'

# 正式环境的日志级别可以在这里配置
# V2
# import logging
# logging.getLogger('root').setLevel('INFO')
# V3
# import logging
# logging.getLogger('app').setLevel('INFO')


# 预发布环境数据库可以在这里配置

DATABASES.update(
    {
        'default': {
                'ENGINE': 'django.db.backends.mysql',  # 默认用mysql
                'NAME': 'quweilong1',  # 数据库名 (默认与APP_ID相同)
                'USER': 'root',  # 你的数据库user
                'PASSWORD': '123456',  # 你的数据库password
                'HOST': '127.0.0.1',  # 开发的时候，使用localhost
                'PORT': '3306',  # 默认3306
    },
    }
)

