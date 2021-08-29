import datetime
import xlrd, csv
from .models import Drill, Drill_Upwell_Data, Drill_Downwell_Data
import numpy as np
from scipy import optimize
import math
def isfloat(value):
  try:
    v = float(value)
    if math.isnan(v) or math.isinf(v):
        return False
    else:
        return True
  except ValueError:
    return False

def load_records(filename, ncol):


    records = []
    message = None
    try:
        if filename.endswith('.xls') or filename.endswith('.xlsx'):
            data = xlrd.open_workbook(filename)
            table = data.sheets()[0]
            nrows = table.nrows  # 获取表的行数
            for i in range(nrows):  # 循环逐行打印
                if i == 0:  # 跳过第一行
                    continue
                records.append(table.row_values(i)[:ncol])

            print(nrows)
        elif filename.endswith('.csv'):
            f = open(filename, encoding="utf8", errors='ignore')
            data = csv.reader(f)

            next(data, None)  # 跳过第一行

            for row in data:
                records.append(row[:ncol])

            f.close()
            print(len(records))
    except Exception as e:
        message = str(e)

    return records, message




def save_upWell(filename, record_id):

    status = True
    message = None

    records, message = load_records(filename, 5)
    if message is not None:
        status = False
        return status, message

    objs = []

    try:
        index = 0
        for record in records:

            if not isfloat(record[0]): #upStress
                continue

            params = {}
            params['index'] = index
            params['upStress'] = record[0]
            params['injectFlow'] = record[1]
            params['backFlow'] = record[2]
            params['inject'] = record[3]
            params['back'] = record[4]
            params['record_id'] = record_id


            objs.append(Drill_Upwell_Data(**params))

            index += 1

        Drill_Upwell_Data.objects.bulk_create(objs)

        message = 'add ' + str(len(objs)) + ' records'
    except Exception as e:
        message = str(e)
        status = False
    return status, message


def save_downWell(filename, record_id):


    status = True
    message = None

    records, message = load_records(filename, 4)
    if message is not None:
        status = False
        return status, message

    objs = []

    try:
        index = 0
        for record in records:
            #for r in record:
            if not isfloat(record[0]): #downStress
                continue

            params = {}

            params['index'] = index
            params['downStress'] = record[0]
            params['measureStress'] = record[1]
            params['downFlow'] = record[2]
            params['downTemperature'] = record[3]
            params['record_id'] = record_id



            objs.append(Drill_Downwell_Data(**params))

            index += 1

        Drill_Downwell_Data.objects.bulk_create(objs)

        message = 'add ' + str(len(objs)) + ' records'
    except Exception as e:
        status = False
        message = str(e)


    return status, message


def piecewise_linear_two(x, x0, b, k1, k2):
    condlist = [x < x0, x >= x0]
    funclist = [lambda x: k1 * x + b, lambda x: k1 * x0 + b + k2 * (x - x0)]

    return np.piecewise(x, condlist, funclist)

def linear_func(x, k, b):
    return k * x + b

def exp_func(x, a, b, c):
    return a * np.exp(-b * x) + c


def my_linear_regreesion(X, y, start_x=None, start_y=None):
    if start_x is None:
        p, e = optimize.curve_fit(linear_func, X, y)
        k = p[0]
        b = p[1]
    else:
        X_shift = X - start_x
        y_shift = y - start_y
        k = X_shift.T.dot(y_shift) / X_shift.T.dot(X_shift)
        b = start_y - k * start_x
    return k, b