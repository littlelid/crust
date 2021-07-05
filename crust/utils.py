import datetime
import xlrd, csv
from .models import Drill, Drill_Upwell_Data, Drill_Downwell_Data


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

