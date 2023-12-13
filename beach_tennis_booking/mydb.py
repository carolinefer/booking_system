import pymysql

data_base = pymysql.connect(host="localhost", user="root", passwd="Carol.190650")

cursor_object = data_base.cursor()

cursor_object.execute("CREATE DATABASE booking")
