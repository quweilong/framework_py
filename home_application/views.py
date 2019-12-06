# -*- coding: utf-8 -*-
from django.shortcuts import render
import json
import urllib.request as urllib3
import requests
from django.shortcuts import render,HttpResponse
from django.shortcuts import render_to_response
from django.http import HttpResponse
import time, datetime

from rest_framework.response import Response








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
    #cpu_usage = get_monitoring_data('	system.cpu.util[,system]')  # CPU使用率
    cpu_trend_chart = get_monitoring_data('system.cpu.util[,user]',"trend_cpu")

    outlet_flow = get_monitoring_data('net.if.out',"trend_outlet_flow")  # 出口流量
    outlet_flow_trend_chart = get_monitoring_data('net.if.out',"trend_outlet_flow")  # 出口流量图

    dict = {}
    dict['memory_data'] = memory_data
    dict['cpu_usage'] = cpu_usage
    dict['outlet_flow'] = outlet_flow
    dict['cpu_trend_chart'] = cpu_trend_chart
    dict['outlet_flow_trend_chart'] = outlet_flow_trend_chart
    print('outlet_flow_trend_chart',outlet_flow_trend_chart)
    return HttpResponse(json.dumps(dict,ensure_ascii=False),content_type="application/json,charset=utf-8")


def get_monitoring_data(monitoring_items,trend="trend"):
    zabbix_url = "http://192.168.0.194/zabbix/api_jsonrpc.php"
    zabbix_header = {"Content-Type": "application/json"}
    zabbix_user = "Admin"
    zabbix_pass = "zabbix"
    auth_code = ""
    host_list = []
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
        "auth": auth_code,
        "id": 1,
    }
    request_obj = requests.post(url=zabbix_url, headers=zabbix_header, data=json.dumps(get_host_data))
    host_obj = json.loads(request_obj.text)['result']
    request_obj.close()

    # 将所有的主机信息显示出来
    for r in host_obj:
        dics = {}
        dics['ip'] = r['interfaces'][0]['ip']
        dics['hostid'] = r['hostid']
        dics['lastvalue'] = ''
        #dics['trend_chart']
        host_list.append(dics)
    print("host_list",host_list)
    # 获取监控对象
    #if trend == "trend_cpu":


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
            "auth": auth_code,
            "id": 1,
            "limit":10
        }
        request_obj = requests.post(url=zabbix_url, headers=zabbix_header, data=json.dumps(get_item_obj))
        item_obj = json.loads(request_obj.text)['result']
        if item_obj:
            itemid = item_obj[0]['itemid']

        for item in item_obj:
            if item['lastvalue'] != 0:

                if monitoring_items == 'vm.memory.size[available]':
                    host_list[i]['lastvalue'] = str(round(int(item['lastvalue'])/1024/1024/1024,2))+"G"
                elif monitoring_items == 'system.cpu.util[,user]':
                    # 往后CPU使用追加值
                    if trend == 'trend_cpu':
                        # 获取时间戳
                        timeStamp = item['lastclock']
                        timeArray = time.localtime(int(timeStamp))
                        otherStyleTime = time.strftime("%H:%M", timeArray)
                        if item['hostid'] == '10084':
                            CPU_TREND_VALUE_10084.append(round(float(item['lastvalue']) * 100,2))
                            host_list[i]['cpu_trend_chart_10084'] = CPU_TREND_VALUE_10084
                            CPU_TREND_TIME_10084.append(otherStyleTime)
                            host_list[i]['cpu_trend_chart_time_10084'] = CPU_TREND_TIME_10084
                        if item['hostid'] == '10305':
                            CPU_TREND_VALUE_10305.append(round(float(item['lastvalue']) * 100,2))
                            host_list[i]['cpu_trend_chart_10305'] = CPU_TREND_VALUE_10305
                        if item['hostid'] == '10306':
                            CPU_TREND_VALUE_10306.append(round(float(item['lastvalue']) * 100,2))
                            host_list[i]['cpu_trend_chart_10306'] = CPU_TREND_VALUE_10306

                    host_list[i]['lastvalue'] = str(round(float(item['lastvalue']) * 100,2))+"%"
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









