from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Drill, Drill_Upwell_Data, Drill_Downwell_Data, Record

from django.core import serializers
from django.core.paginator import Paginator
from django.http import QueryDict
from django.http import HttpResponse

from django.http.multipartparser import MultiPartParser

import os, datetime

from django.forms.models import model_to_dict

from .utils import save_downWell, save_upWell
from .calculate import estimate_pb, estimate_pr, estimate_ps_tangent, estimate_ps_muskat, estimate_ps_dp_dt, estimate_ps_dt_dp

import json, time

import logging

# 实例化logging对象,并以当前文件的名字作为logger实例的名字
logger = logging.getLogger(__name__)
# 生成一个名字叫做 collect 的日志实例
logger_c = logging.getLogger('file')

# Create your views here.
def index(request):
    x = {}
    x["a"] = 1
    x["b"] = 1
    x["c"] = 1
    return JsonResponse(x)


@csrf_exempt
def drill(request, drill_id=None):
    logger.info(request.method + ' '+ request.path_info)

    res = {
        'data': None,
        'message': '',
        'status': 'success',
    }

    if request.method == 'GET':

        objs = []
        try:
            if drill_id is not None:  # GET "/drill/{id}" 获得id的钻孔
                objs = Drill.objects.filter(pk=drill_id)

            else:   #GET "/drill?pageCur=1&pageSize=10" 获得所有数据（第pageCur页，每页pageSize个，页号从1开始），返回list
                pageCur = request.GET.get('pageCur')
                pageSize = request.GET.get('pageSize')

                objs = Drill.objects.all()


                if(pageCur is not None and pageSize is not None):
                    pageCur = int(pageCur)
                    pageSize = int(pageSize)
                    p = Paginator(objs, pageSize)
                    if(pageCur <= p.num_pages and pageCur > 0):
                        objs = p.page(pageCur).object_list
                    else:
                        objs = []

            res['message'] = "get %s drill" % len(objs)
            res['status'] = 'success' if len(objs) >= 1 else 'fail'
        except Exception as e:

            res['message'] = "get drill: " + str(e)
            res['status'] = 'fail'

        serialized_obj = serializers.serialize('json', objs)
        objs = json.loads(serialized_obj)

        for obj in objs:
            obj['fields']['id'] = obj['pk']

        res['data'] = objs

        #serialized_obj = json.dumps(objs)
        #return HttpResponse(serialized_obj, content_type='application/json')

    if request.method == 'POST':

        try:
            params = request.POST.dict()
            #print(params)
            params.pop('id', None)
            obj = Drill(**params)

            obj.save()

            res['message'] = "post one drill"
            res['status'] = 'success'

            logger.info('saved one Drill: ' + str(params))
        except Exception as e:
            res['message'] = "post one drill: " + str(e)
            res['status'] = 'fail'

    elif request.method == 'DELETE':
        print(drill_id)

        objs = Drill.objects.filter(pk=drill_id)
        num_objs = len(objs)
        objs.delete()

        res['message'] = "delete %s drill" % num_objs
        res['status'] = 'success' if num_objs == 1 else 'fail'




    elif request.method == 'PUT':

        try:
            obj = Drill.objects.get(pk=drill_id)

            params = MultiPartParser(request.META, request, request.upload_handlers).parse()[0]
            params = params.dict()

            print(params)
            for k, v in params.items():
                #print(k, v)
                if (hasattr(obj, k)):
                    setattr(obj, k, v)

            obj.save()

            res['message'] = "update drill %s" % drill_id
            res['status'] = 'success'
            #params['id'] = obj.id
            #logger.info('updated one Drill: ' + str(params))

        except Exception as e:
            res['message'] = "update drill %s: %s" % (drill_id, str(e))
            res['status'] = 'fail'

    logger.info(res['status'] + ' ' + res['message'])

    return JsonResponse(res)


@csrf_exempt
def fileUpload(request, drill_id, data_type):
    logger.info(request.method + ' ' + request.path_info)
    #print(drill_id, data_type)
    res = {
        'data': None,
        'message': 'file upload',
        'status': 'success',
    }

    try:
        drill = Drill.objects.filter(pk=drill_id)

        if request.method == "POST":  # 请求方法为POST时，进行处理
            myFile = request.FILES.get("file", None)  # 获取上传的文件，如果没有文件，则默认为None
            #print(myFile, myFile.size)
            filename = "./crust/static/files/" + myFile.name
            f = open(filename, 'wb')
            for chunk in myFile.chunks():
                f.write(chunk)
            f.close()


            now = datetime.datetime.now()
            record = Record(data_type=data_type, drill_id=drill_id, time=now)
            record.save()

            if data_type == "upWell":
                status, message = save_upWell(filename, record.id)
            else:
                status, message = save_downWell(filename, record.id)

            if status is False:
                res['status'] = 'fail'
                res['message'] = 'file upload %s: %s' % (myFile.name, message)
    except Exception as e:
        res['status'] = 'fail'
        res['message'] = 'file upload %s: %s' % (myFile.name, str(e))

    logger.info(res['status'] + ' ' + res['message'])
    return JsonResponse(res)


@csrf_exempt
def record(request, drill_id, data_type):
    logger.info(request.method + ' ' + request.path_info)
    res = {
        'data': None,
        'message': 'record',
        'status':  'success',
    }

    if request.method == "DELETE":
        try:

            objs = Record.objects.filter(drill_id=drill_id)
            num_objs = len(objs)
            objs.delete()
            res['message'] = 'delete ' + str(num_objs) + ' obj'

        except Exception as e:
            res['message'] = str(e)
            res['status'] = 'fail'

    elif request.method == "GET":
        objs = Record.objects.filter(drill_id=drill_id, data_type=data_type).order_by('-time')
        if len(objs) == 0:
            res['message'] = 'no data'
            res['status'] = 'fail'
        else:
            record_id = objs[0].id
            print('record id is', record_id)
            try:
                data = {}
                if data_type == 'upWell':
                    objs = Drill_Upwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
                    objs = [model_to_dict(obj) for obj in objs]

                    data['axisX'] = list(range(len(objs)))
                    fields = ['upStress', 'injectFlow', 'backFlow', 'inject', 'back']
                    for field in fields:
                        data[field] = [ obj[field] for obj in objs]

                    #print(data)
                    print(data.keys())

                else:
                    objs = Drill_Downwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
                    objs = [model_to_dict(obj) for obj in objs]

                    data['axisX'] = list(range(len(objs)))
                    fields = ['downStress', 'measureStress', 'downFlow', 'downTemperature']
                    for field in fields:
                        data[field] = [obj[field] for obj in objs]

                res['data'] = data
                res['message'] = 'get'

            except Exception as e:
                res['message'] = str(e)
                res['status'] = 'fail'

    logger.info(res['status'] + ' ' + res['message'])

    return JsonResponse(res)


def get_pressure(drill_id, data_type):
    now0 = time.time()
    objs = Record.objects.filter(drill_id=drill_id, data_type=data_type).order_by('-time')
    now1 = time.time()
    if len(objs) == 0:
        return None
    else:
        record_id = objs[0].id

    pressure = []
    if data_type == "upWell":
        objs = Drill_Upwell_Data.objects.filter(record_id__exact=record_id).order_by('index')

        objs = list(objs)

        pressure = [float(obj.upStress) for obj in objs]

        print("pressure len", len(pressure))
    else:
        objs = Drill_Downwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
        objs = list(objs)
        pressure = [float(obj.downStress) for obj in objs]
        print("pressure len", len(pressure))
    #print(now4-now3, now3-now2, now2-now1, now1-now0)
    if len(pressure) > 0:
        return pressure
    else:
        return None


@csrf_exempt
def calculate_pb(request, drill_id, data_type):
    now0 = time.time()
    logger.info(request.method + ' ' + request.path_info)
    print(request, drill_id, data_type)
    res = {
        'data': None,
        'message': 'calculate_pb',
        'status': 'success',
    }
    st_sel = int(request.GET['start'])
    et_sel = int(request.GET['end'])

    now1 = time.time()
    pressure = get_pressure(drill_id, data_type)
    if pressure is None:
        res['message'] = 'no data'
        res['status'] = 'fail'
        return JsonResponse(res)

    now2 = time.time()
    est = estimate_pb(pressure, st_sel, et_sel)
    now3 = time.time()
    if est is None:
        res['message'] = 'error in estimate_pb'
        res['status'] = 'fail'
        return JsonResponse(res)
    res['data'] = est
    logger.info(res['status'] + ' ' + res['message'])
    now4 = time.time()
    print(now4 - now3, now3 - now2, now2 - now1, now1 - now0)
    return JsonResponse(res)

@csrf_exempt
def calculate_pr(request, drill_id, data_type):
    logger.info(request.method + ' ' + request.path_info)
    res = {
        'data': None,
        'message': 'calculate_pb',
        'status': 'success',
    }

    st_sel = int(request.GET['start'])
    et_sel = int(request.GET['end'])

    pressure = get_pressure(drill_id, data_type)
    if pressure is None:
        res['message'] = 'no data'
        res['status'] = 'fail'
        return JsonResponse(res)

    est = estimate_pr(pressure, st_sel, et_sel)
    if est is None:
        res['message'] = 'error in estimate_pr'
        res['status'] = 'fail'

        return JsonResponse(res)

    res['data'] = est

    logger.info(res['status'] + ' ' + res['message'])
    return JsonResponse(res)



@csrf_exempt
def calculate_ps(request, drill_id, data_type):
    logger.info(request.method + ' ' + request.path_info)
    print(request, drill_id, data_type)
    res = {
        'data': None,
        'message': 'calculate_ps',
        'status': 'success',
    }

    st_sel = int(request.GET['start'])
    et_sel = int(request.GET['end'])
    method = int(request.GET['method'])

    pressure = get_pressure(drill_id, data_type)
    if pressure is None:
        res['message'] = 'no data'
        res['status'] = 'fail'
        return JsonResponse(res)

    if method == 1:
        est = estimate_ps_tangent(pressure, st_sel, et_sel)
    elif method == 2:
        est = estimate_ps_muskat(pressure, st_sel, et_sel)
    elif method == 3:
        est = estimate_ps_dp_dt(pressure, st_sel, et_sel)
    elif method == 4:
        est = estimate_ps_dt_dp(pressure, st_sel, et_sel)

    if est is None:
        res['status'] = 'fail'
        res['message'] = 'error in estimate_ps'
        return JsonResponse(res)

    res['data'] = est

    logger.info(res['status'] + ' ' + res['message'])

    return JsonResponse(res)
