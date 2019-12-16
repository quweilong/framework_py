# -*- coding: utf-8 -*-
from django.shortcuts import render
import json
import urllib.request as urllib3
import requests
from django.shortcuts import render, HttpResponse
from django.shortcuts import render_to_response
from django.http import HttpResponse
import time, datetime
import redis
from rest_framework.response import Response
import re

# 开发框架中通过中间件默认是需要登录态的，如有不需要登录的，可添加装饰器login_exempt
# 装饰器引入 from blueapps.account.decorators import login_exempt
def home(request):
    """
    首页
    """
    return render(request, 'home_application/index_home.html')


def dev_guide(request):
    """
    开发指引
    """
    return render(request, 'home_application/dev_guide.html')


def contact(request):
    """
    联系页
    """
    return render(request, 'home_application/contact.html')


def screen(request):
    return render(request, 'home_application/screen_one.html')


def detailspage(request):
    return render(request, 'home_application/detailspage.html')


CPU_TREND_VALUE_10084 = []
CPU_TREND_TIME_10084 = []
CPU_TREND_VALUE_10305 = []
CPU_TREND_VALUE_10306 = []

OUTLET_FLOW_TREND_VALUE_10084 = []
OUTLET_FLOW_TREND_TIME_10084 = []
OUTLET_FLOW_TREND_VALUE_10305 = []
OUTLET_FLOW_TREND_VALUE_10306 = []


def get_data(request):
    memory_data = get_monitoring_data('vm.memory.size[available]')  # 可用内存
    cpu_usage = get_monitoring_data('system.cpu.util[,user]')  # CPU使用率
    # cpu_usage = get_monitoring_data('	system.cpu.util[,system]')  # CPU使用率
    cpu_trend_chart = get_monitoring_data('system.cpu.util[,user]', "trend_cpu")

    outlet_flow = get_monitoring_data('net.if.out', "trend_outlet_flow")  # 出口流量
    outlet_flow_trend_chart = get_monitoring_data('net.if.out', "trend_outlet_flow")  # 出口流量图
    dict = {}
    dict['memory_data'] = memory_data
    dict['cpu_usage'] = cpu_usage
    dict['outlet_flow'] = outlet_flow
    dict['cpu_trend_chart'] = cpu_trend_chart
    dict['outlet_flow_trend_chart'] = outlet_flow_trend_chart
    return HttpResponse(json.dumps(dict, ensure_ascii=False), content_type="application/json,charset=utf-8")


def login_zabbix():
    """
    登录zabbix方法
    :return: zabbix_url,zabbix_header,auth_code
    """
    zabbix_url = "http://192.168.0.194/zabbix/api_jsonrpc.php"
    zabbix_header = {"Content-Type": "application/json"}
    zabbix_user = "Admin"
    zabbix_pass = "zabbix"
    auth_code = ""
    # 用户认证信息
    auth_data = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params":
            {
                "user": zabbix_user,
                "password": zabbix_pass
            },
        "id": 0
    }
    # 创建 request 对象  构造请求数据
    request_obj = requests.post(url=zabbix_url, headers=zabbix_header, data=json.dumps(auth_data))
    login_obj = json.loads(request_obj.text)
    request_obj.close()
    if 'result' in login_obj:
        auth_code = login_obj['result']
    dict = {}
    dict['zabbix_url'] = zabbix_url
    dict['zabbix_header'] = zabbix_header
    dict['auth_code'] = auth_code
    return dict

def get_detailspage_info(request):
    """
    获取详细页所有主机信息
    :param request:
    :return:
    """
    login_obj = login_zabbix()                              # 登录zabbix
    host_info = get_host_info(login_obj)                    # 获取主机信息
    cpu_info = get_cpu(login_obj)                           # 获取CPU
    rw_rate =get_rw_rate(login_obj)                         # 获取磁盘读写速率
    memory_utilization = get_memory_utilization(login_obj)  # 内存使用率
    net_traffic = get_net_traffic(login_obj)                # 网卡流量
    warned_message = get_warned_message(login_obj)          # 告警信息
    disk_utilization = get_disk_utilization(login_obj)
    dict = {}
    dict['host_info'] = host_info
    dict['cpu_info'] = cpu_info
    dict['rw_rate'] = rw_rate
    dict['memory_utilization'] = memory_utilization
    dict['net_traffic'] = net_traffic
    dict['warned_message'] = warned_message
    dict['disk_utilization'] = disk_utilization
    return HttpResponse(json.dumps(dict, ensure_ascii=False), content_type="application/json,charset=utf-8")

def get_memory_utilization(login_obj):
    """获取内存使用率"""
    host_obj = get_host(login_obj)  # 获取主机
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "vm.memory.size[pavailable]"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    # 向zabbix发起请求
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    memory_list = json.loads(request_obj.text)['result']
    request_obj.close()
    # 获取时间戳
    timeStamp = memory_list[0]['lastclock']
    timeArray = time.localtime(int(timeStamp))
    otherStyleTime = time.strftime("%H:%M", timeArray)
    # 用总百分比减去cpu空闲率就是cpu使用率
    memory_utilization = memory_list[0]['lastvalue']
    conn = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
    conn.rpush("memory_utilization", memory_utilization)
    conn.rpush("memory_sysyem_time", otherStyleTime)
    if conn.llen("memory_utilization") > 15:
        conn.blpop("memory_utilization", 1)
    if conn.llen("memory_sysyem_time") > 15:
        conn.blpop("memory_sysyem_time", 1)
    dict = {}
    dict['memory_utilization'] = conn.lrange("memory_utilization", 0, -1)
    dict['memory_sysyem_time'] = conn.lrange("memory_sysyem_time", 0, -1)
    return dict



def get_host(login_obj):
    """
    获取主机
    :return:
    """
    host_list = []
    hostid = '10084'
    data = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": [
                "hostid",
                "host",
                "name"
            ],
            "selectInterfaces": [
                "ip"
            ]
        },
        "id": 1,
        "auth": login_obj['auth_code']
    }
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    host_obj = json.loads(request_obj.text)['result']
    request_obj.close()
    for obj in host_obj:
        if obj['hostid'] == hostid:
            host_obj = obj
    return host_obj

def get_cpu(login_obj):
    """获取cpu使用率"""
    host_obj = get_host(login_obj)  # 获取主机
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "system.cpu.util[,idle]"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    # 获取cpu信息列表
    # 华三防火墙跳过
    # if len(cpu_list) == 0:
    #     continue
    # 将cpu空闲率取出来
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    cpu_obj = json.loads(request_obj.text)['result']
    request_obj.close()
    # 获取时间戳
    timeStamp = cpu_obj[0]['lastclock']
    timeArray = time.localtime(int(timeStamp))
    otherStyleTime = time.strftime("%H:%M", timeArray)
    idle_percent = cpu_obj[0]['lastvalue']
    # 用总百分比减去cpu空闲率就是cpu使用率
    cpu_unilization = str(round(100 - float(idle_percent), 2))
    conn = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
    conn.rpush("unilization",cpu_unilization)
    conn.rpush("sysyem_time",otherStyleTime)
    if conn.llen("unilization") >15:
        conn.blpop("unilization",1)
    if conn.llen("sysyem_time") >15:
        conn.blpop("sysyem_time", 1)
    dict = {}
    dict['cpu_unilization'] = conn.lrange("unilization",0,-1)
    dict['systemtime'] = conn.lrange("sysyem_time",0,-1)
    return dict

def get_rw_rate(login_obj):
    """获取磁盘读写速率"""
    host_obj = get_host(login_obj)  # 获取主机
    # 创建一个空字典来存放磁盘读写速率
    # 构造请求体
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "vfs.dev.read.rate[sda]"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    # 向zabbix请求数据
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    read_list = json.loads(request_obj.text)['result']
    request_obj.close()
    # 取出磁盘读速率,放进字典中

    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "vfs.dev.write.rate[sda]"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    # 发起请求获取磁盘写入速率
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    write_list = json.loads(request_obj.text)['result']
    request_obj.close()
    # 获取时间戳
    timeStamp = read_list[0]['lastclock']
    timeArray = time.localtime(int(timeStamp))
    otherStyleTime = time.strftime("%H:%M", timeArray)
    write_rate = write_list[0]['lastvalue']
    read_rate = read_list[0]['lastvalue']

    conn = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
    conn.rpush("write_rate", write_rate)
    conn.rpush("read_rate", read_rate)
    conn.rpush("disk_sysyem_time", otherStyleTime)
    if conn.llen("write_rate") > 15:
        conn.blpop("write_rate", 1)
    if conn.llen("read_rate") > 15:
        conn.blpop("read_rate", 1)
    if conn.llen("disk_sysyem_time") > 15:
        conn.blpop("disk_sysyem_time", 1)
    dict = {}
    dict['write_rate'] = conn.lrange("write_rate", 0, -1)
    dict['read_rate'] = conn.lrange("read_rate", 0, -1)
    dict['disk_sysyem_time'] = conn.lrange("disk_sysyem_time", 0, -1)
    return dict


def get_host_info(login_obj):
    """
    获取主机信息
    :return:
    """
    host_obj = get_host(login_obj)      # 获取主机
    # 构造获取操作系统信息的请求体
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "system.sw.os"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    monitor_obj = json.loads(request_obj.text)['result']
    request_obj.close()
    # 华三防火墙没有操作系统值,故跳过
    # if len(monitor_obj) == 0:
    #     continue
    # 取出操作系统信息
    os_name = monitor_obj[0]['lastvalue']
    # 构建获取主机运行时间请求体
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "system.uptime"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    monitor_obj = json.loads(request_obj.text)['result']
    request_obj.close()
    lifetime = monitor_obj[0]['lifetime']
    dict = {}
    dict['os_name'] = os_name[0:os_name.find("(")]
    dict['uptime'] = lifetime
    dict['host'] = host_obj['host']
    dict['name'] = host_obj['name']
    dict['ip'] = host_obj['interfaces'][0]['ip']
    return dict

def get_warned_message(login_obj):
    """获取告警信息"""
    host_obj = get_host(login_obj)  # 获取主机
    # 构建获取触发器信息请求体
    data = {
        "jsonrpc": "2.0",
        "method": "trigger.get",
        "params": {
            "output": "extend",
            "filter": {
                "value": 1
            },
            "sortfield": "priority",
            "sortorder": "DESC",
            "min_severity": 2,
            "skipDependent": 1,
            "monitored": 1,
            "active": 1,
            "expandDescription": 1,
            "selectHosts": ['host'],
            "selectGroups": ['name'],
            "only_true": 1
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    trigger_list = json.loads(request_obj.text)['result']
    request_obj.close()
    # 创建一个空列表存储所有触发器告警信息
    warned_list = list()
    for i in trigger_list:
        trigger_dict = dict()
        # 告警信息
        trigger_dict['description'] = i['description']
        # 告警的主机名字
        trigger_dict['name'] = i['hosts'][0]['host']
        # 判断告警程度
        if i['priority'] == '2':
            trigger_dict['priority'] = '警告'
        elif i['priority'] == '3':
            trigger_dict['priority'] = '一般严重'
        elif i['priority'] == '4':
            trigger_dict['priority'] = '严重'
        elif i['priority'] == '5':
            trigger_dict['priority'] = '灾难'
        # 触发器ID
        trigger_dict['triggerid'] = i['triggerid']
        # 触发时间
        # 获取时间戳
        timeStamp = i['lastchange']
        timeArray = time.localtime(int(timeStamp))
        otherStyleTime = time.strftime("%H:%M", timeArray)
        trigger_dict['trigger_time'] = otherStyleTime
        if i['status'] == '0':
            trigger_dict['status'] = '问题'
        # 将构建触发器告警信息存入warned_list中
        warned_list.append(trigger_dict)
    return warned_list

def get_net_traffic(login_obj):
    # 获取接口流入和流出流量
    host_obj = get_host(login_obj)  # 获取主机
    # 构造请求体
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "net.if.in"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    # 向zabbix请求流入流量数据
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    net_in_list = json.loads(request_obj.text)['result']
    request_obj.close()
    for i in net_in_list:
        # 流入流量
        if re.match('^net.if.in\["\w+"\]$', i['key_']):
            received_traffic = str(round(float(i['lastvalue']) / 1024, 2))
        # 丢失的数据包'net.if.in["eno16777984"]'
        if re.match('^net.if.in\["(\w)+",dropped\]$', i['key_']):
            received_dropped = str(round(float(i['lastvalue']) / 1024, 2))
        # 错误的数据包
        if re.match('^net.if.in\["(\w)+",errors\]$', i['key_']):
            received_errors = str(round(float(i['lastvalue']) / 1024, 2))
    # 构造流出流量请求体
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "net.if.out"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    # 向zabbix请求流出流量数据
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    net_out_list = json.loads(request_obj.text)['result']
    request_obj.close()
    for i in net_out_list:
        # 流出的流量
        if re.match('^net.if.out\["\w+"\]$', i['key_']):
            sent_traffic = str(round(float(i['lastvalue']) / 1024, 2))
        # 丢失的数据包'net.if.in["eno16777984"]'
        if re.match('^net.if.out\["(\w)+",dropped\]$', i['key_']):
            sent_dropped = str(round(float(i['lastvalue']) / 1024, 2))
        # 错误的数据包
        if re.match('^net.if.out\["(\w)+",errors\]$', i['key_']):
            sent_errors = str(round(float(i['lastvalue']) / 1024, 2))
    # 获取时间戳
    timeStamp = net_out_list[0]['lastclock']
    timeArray = time.localtime(int(timeStamp))
    otherStyleTime = time.strftime("%H:%M", timeArray)
    conn = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
    conn.rpush("received_traffic", received_traffic)
    conn.rpush("sent_traffic", sent_traffic)
    conn.rpush("traffic_sysyem_time", otherStyleTime)
    if conn.llen("received_traffic") > 15:
        conn.blpop("received_traffic", 1)
    if conn.llen("sent_traffic") > 15:
        conn.blpop("sent_traffic", 1)
    if conn.llen("traffic_sysyem_time") > 15:
        conn.blpop("traffic_sysyem_time", 1)
    dict = {}
    dict['received_traffic'] = conn.lrange("received_traffic", 0, -1)
    dict['sent_traffic'] = conn.lrange("sent_traffic", 0, -1)
    dict['traffic_sysyem_time'] = conn.lrange("traffic_sysyem_time", 0, -1)
    return dict

def get_disk_utilization(login_obj):
    """获取磁盘使用率"""
    host_obj = get_host(login_obj)  # 获取主机
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "vfs.fs.size[/boot,pused]"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    boot_disk_list = json.loads(request_obj.text)['result']
    if len(boot_disk_list) == 0:
        return
    # /boot磁盘使用率
    boot_utilization = boot_disk_list[0]['lastvalue']
    data = {
        "jsonrpc": "2.0",
        "method": "item.get",
        "params": {
            "output": "extend",
            "hostids": host_obj['hostid'],
            "search": {
                "key_": "vfs.fs.size[/,pused]"
            },
            "sortfield": "name"
        },
        "auth": login_obj['auth_code'],
        "id": 1
    }
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'],
                                data=json.dumps(data))
    root_disk_list = json.loads(request_obj.text)['result']
    # 根目录使用率
    root_utilization = root_disk_list[0]['lastvalue']
    hard_disk_mount_point = ["/","/boot"]
    disk_usage = [root_utilization,boot_utilization]
    dict ={}
    dict['hard_disk_mount_point'] = hard_disk_mount_point
    dict['disk_usage'] = disk_usage
    return dict

def get_monitoring_data(monitoring_items, trend="trend"):
    login_obj = login_zabbix()
    host_list = []
    # 获取主机的信息（用http.get方法）
    get_host_data = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": "extend",
            "selectInterfaces": [
                "ip"
            ]
        },
        "auth": login_obj['auth_code'],
        "id": 1,
    }
    request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'], data=json.dumps(get_host_data))
    host_obj = json.loads(request_obj.text)['result']
    request_obj.close()

    # 将所有的主机信息显示出来
    for r in host_obj:
        dics = {}
        dics['ip'] = r['interfaces'][0]['ip']
        dics['hostid'] = r['hostid']
        dics['lastvalue'] = ''
        # dics['trend_chart']
        host_list.append(dics)
    # 获取监控对象
    # if trend == "trend_cpu":

    for i, item in enumerate(host_list):
        get_item_obj = {
            "jsonrpc": "2.0",
            "method": "item.get",
            "params": {
                "output": "extend",
                "hostids": item['hostid'],
                "search": {
                    "key_": monitoring_items
                },
            },
            "auth": login_obj['auth_code'],
            "id": 1,
            "limit": 10
        }

        request_obj = requests.post(url=login_obj['zabbix_url'], headers=login_obj['zabbix_header'], data=json.dumps(get_item_obj))
        item_obj = json.loads(request_obj.text)['result']
        if item_obj:
            itemid = item_obj[0]['itemid']

        for item in item_obj:
            if item['lastvalue'] != 0:

                if monitoring_items == 'vm.memory.size[available]':
                    host_list[i]['lastvalue'] = str(round(int(item['lastvalue']) / 1024 / 1024 / 1024, 2)) + "G"
                elif monitoring_items == 'system.cpu.util[,user]':
                    # 往后CPU使用追加值
                    if trend == 'trend_cpu':
                        # 获取时间戳
                        timeStamp = item['lastclock']
                        timeArray = time.localtime(int(timeStamp))
                        otherStyleTime = time.strftime("%H:%M", timeArray)
                        if item['hostid'] == '10084':
                            CPU_TREND_VALUE_10084.append(round(float(item['lastvalue']) * 100, 2))
                            host_list[i]['cpu_trend_chart_10084'] = CPU_TREND_VALUE_10084
                            CPU_TREND_TIME_10084.append(otherStyleTime)
                            host_list[i]['cpu_trend_chart_time_10084'] = CPU_TREND_TIME_10084
                        if item['hostid'] == '10305':
                            CPU_TREND_VALUE_10305.append(round(float(item['lastvalue']) * 100, 2))
                            host_list[i]['cpu_trend_chart_10305'] = CPU_TREND_VALUE_10305
                        if item['hostid'] == '10306':
                            CPU_TREND_VALUE_10306.append(round(float(item['lastvalue']) * 100, 2))
                            host_list[i]['cpu_trend_chart_10306'] = CPU_TREND_VALUE_10306

                    host_list[i]['lastvalue'] = str(round(float(item['lastvalue']) * 100, 2)) + "%"
                elif monitoring_items == 'net.if.out':
                    if trend == 'trend_outlet_flow':
                        # 获取时间戳
                        timeStamp = item['lastclock']
                        timeArray = time.localtime(int(timeStamp))
                        otherStyleTime = time.strftime("%H:%M", timeArray)
                        if item['hostid'] == '10084':
                            OUTLET_FLOW_TREND_VALUE_10084.append(round(float(item['lastvalue']) / 1024, 2))
                            host_list[i]['outlet_flow_trend_chart_10084'] = OUTLET_FLOW_TREND_VALUE_10084
                            OUTLET_FLOW_TREND_TIME_10084.append(otherStyleTime)
                            host_list[i]['outlet_flow_trend_chart_time_10084'] = OUTLET_FLOW_TREND_TIME_10084
                        if item['hostid'] == '10305':
                            OUTLET_FLOW_TREND_VALUE_10305.append(round(float(item['lastvalue']) / 1024, 2))
                            host_list[i]['outlet_flow_trend_chart_10305'] = OUTLET_FLOW_TREND_VALUE_10305
                        if item['hostid'] == '10306':
                            OUTLET_FLOW_TREND_VALUE_10306.append(round(float(item['lastvalue']) / 1024, 2))
                            host_list[i]['outlet_flow_trend_chart_10306'] = OUTLET_FLOW_TREND_VALUE_10306

                    host_list[i]['lastvalue'] = str(round(int(item['lastvalue']) / 1024, 2)) + "M"
        request_obj.close()

    return host_list
