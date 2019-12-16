# -*- coding: utf-8 -*-
# from django.test import TestCase

#   pip install psycopg2   插入下面两个包
import psycopg2
import time


#  创建连接
conn = psycopg2.connect(database="postgres", user="postgres", password="123456", host="127.0.0.1", port="5432")
cur = conn.cursor()

i = 1
while i <= 500:         # 此处控制创建多少张表
    #   字段可直接按照下面格式修改
    cur.execute('''CREATE TABLE''' + " testsy_" + str(i) +
           '''( col_date date,
                col_char char,
                col_char10 char(10),
                col_char100 char(100),
                col_varchar varchar,
                col_varchar10 varchar(10),
                col_varchar100 varchar(100),
                col_numeric numeric,
                col_numeric10 numeric(10),
                col_float4 float4,
                col_float8 float8,
                col_int2 int2,
                col_int4 int4,
                col_int8 int8,
                col_timestamp timestamp,
                col_timestamp2 timestamp,
                col_timestamptz timestamptz,
                col_text text
           );
           ''')
    i += 1
conn.commit()
print("Table created successfully")



i = 1
while i <= 500:       # 此处和创建的表张数相同  比如 创500张表  此处也是500
    j = 1
    while j <100:   # 此处控制插入的条数
        current_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        #  {} 表示占位符  对应 .format后面的数据  一一对应
        sql = """insert into testsy_{} (col_date,col_char,col_char10,col_char100,col_varchar,col_varchar10,col_varchar100,col_numeric,col_numeric10,
                col_float4,col_float8,col_int2,col_int4,col_int8,col_timestamp,col_timestamp2,col_timestamptz,col_text)values ('{}','{}','{}','{}','{}','{}','{}',{},{},{},{},{},{},{},'{}','{}','{}','{}')
              """.format(i,current_date,'a','第'+str(j)+'条','char100类型第'+str(j)+'条','varchar类型第'+str(j)+'条','第'+str(j)+'条',
                          'varchar100类型第'+ str(j)+ '条',j,j,j+0.5,j+0.005,j,j,j,current_date,current_date,current_date,'text类型第'+str(j)+'条')
        cur.execute(sql)
        j += 1

    i += 1
print("insert data successfully")
conn.commit()
conn.close()





