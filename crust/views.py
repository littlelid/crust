from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Drill, Drill_Upwell_Data, Drill_Downwell_Data, Record, Calculation
from scipy.signal import savgol_filter
from django.core import serializers
from django.core.paginator import Paginator
from django.http import QueryDict
from django.http import HttpResponse
from scipy.ndimage.filters import uniform_filter1d

from django.http.multipartparser import MultiPartParser

import os, datetime
import numpy as np
from django.forms.models import model_to_dict

from .utils import save_downWell, save_upWell
from .calculate import estimate_pb, estimate_pr, estimate_ps_tangent, estimate_ps_muskat, estimate_ps_dp_dt, estimate_ps_dt_dp, estimate_ps_dp_dt_robust, estimate_ps_dt_dp_robust

from scipy.ndimage.filters import uniform_filter1d


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
def drill_count(request):
    logger.info(request.method + ' ' + request.path_info)

    res = {
        'data': 0,
        'message': '',
        'status': 'success',
    }

    if request.method == 'GET':
        try:
            cnt = Drill.objects.all().count()

            res['data'] = cnt


            res['message'] = "drill cnt %s" % cnt
            res['status'] = 'success'
        except Exception as e:

            res['message'] = "drill cnt " + str(e)
            res['status'] = 'fail'

    logger.info(res['status'] + ' ' + res['message'])

    return JsonResponse(res)


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

            records = Record.objects.filter(drill_id=obj['pk'])

            deeps = []
            samplingFreqs = []
            for record in records: #每个upWell 和 downWell都有一个record
                if record.deep not in deeps:
                    deeps.append(record.deep)
                    samplingFreqs.append(record.samplingFreq)

            #samplingFreqs = [ record.samplingFreq for record in records]
            idxs = np.argsort([float(deep) for deep in deeps])
            deeps = [ deeps[idx] for idx in idxs]
            samplingFreqs = [samplingFreqs[idx] for idx in idxs]

            obj['fields']['deep'] = deeps
            obj['fields']['samplingFreq'] = samplingFreqs




        res['data'] = objs

        #serialized_obj = json.dumps(objs)
        #return HttpResponse(serialized_obj, content_type='application/json')

    elif request.method == 'POST':

        try:
            params = request.POST.dict()
            #print(params)
            params.pop('id', None)

            drill = Drill(**params)

            drill.save()

            # add deep
            #now = datetime.datetime.now()
            #for data_type in ['upWell', 'downWell']:
            #    record = Record(data_type=data_type, drill_id=drill.id, time=now, deep=params['max_deep'], samplingFreq=1)
            #    record.save()

            #    logger.info('add new deep %s for Drill %s' % (params['max_deep'], drill.id))

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

            #params = MultiPartParser(request.META, request, request.upload_handlers).parse()[0]
            #params = params.dict()

            params = QueryDict(request.body, encoding=request.encoding)

            logger.info(params)


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
def calculation(request, drill_id, deep, data_type):
    logger.info(request.method + ' ' + request.path_info)

    res = {
        'data': None,
        'message': '',
        'status': 'success',
    }

    objs = Record.objects.filter(drill_id=drill_id, deep=deep, data_type=data_type) #.order_by('-time')
    if len(objs) == 0:
        res['message'] = 'no record'
        res['status'] = 'fail'
        return JsonResponse(res)

    assert len(objs) == 1

    record_id = objs[0].id
    print('record id is', record_id)

    if request.method == 'GET':
        try:
            stress_type = request.GET.get('stress_type')
            method = request.GET.get('method')

            objs = Calculation.objects.filter(record_id__exact=record_id, stress_type=stress_type, method=method).order_by('-time')

            if len(objs) >= 1:
                objs = objs[0:1]

            serialized_obj = serializers.serialize('json', objs)
            objs = json.loads(serialized_obj)


            for obj in objs:
                obj['fields']['id'] = obj['pk']

            res['data'] = objs
            res['message'] = "get %s calculation" % len(objs)
            res['status'] = 'success' if len(objs) > 0 else 'fail'

            logger.info(res['message'])

        except Exception as e:
            logger.info(str(e))
            res['message'] = str(e)
            res['status'] = 'fail'

    elif request.method == 'POST':

        try:
            params = request.POST.dict()

            logger.info(params)
            print(params)

            params['time'] = datetime.datetime.now()
            params['record_id'] = record_id

            obj = Calculation(**params)
            obj.save()

            res['message'] = "post one calculation"
            res['status'] = 'success'

            logger.info(res['message'])
        except Exception as e:
            logger.info(str(e))
            res['message'] = str(e)
            res['status'] = 'fail'



    return JsonResponse(res)


@csrf_exempt
def fileUpload(request, drill_id, deep, data_type):
    logger.info(request.method + ' ' + request.path_info)
    #print(drill_id, data_type)
    res = {
        'data': None,
        'message': 'file upload',
        'status': 'success',
    }

    try:
        #drill = Drill.objects.filter(pk=drill_id)

        if request.method == "POST":  # 请求方法为POST时，进行处理
            myFile = request.FILES.get("file", None)  # 获取上传的文件，如果没有文件，则默认为None
            #print(myFile, myFile.size)
            filename = "./crust/static/files/" + myFile.name
            f = open(filename, 'wb')
            for chunk in myFile.chunks():
                f.write(chunk)
            f.close()

            objs = Record.objects.filter(drill_id=drill_id, deep=deep, data_type=data_type, )
            if len(objs) == 0:
                res['message'] = 'deep %s not exists for Drill %s' % (deep, drill_id)
                res['status'] = 'fail'
                return JsonResponse(res)

            assert len(objs) == 1

            record = objs[0]
            now = datetime.datetime.now()
            record.time = now
            record.save()

            if data_type == "upWell":
                objs = Drill_Upwell_Data.objects.filter(record_id__exact=record.id)
                objs.delete()
                print("delete old pressure")
                status, message = save_upWell(filename, record.id)
            else:
                objs = Drill_Downwell_Data.objects.filter(record_id__exact=record.id)
                objs.delete()
                print("delete old pressure")
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
def record(request, drill_id, deep=None, data_type=None):
    #tt0 = time.time()
    logger.info(request.method + ' ' + request.path_info)
    res = {
        'data': None,
        'message': 'record',
        'status':  'success',
    }

    if request.method == "DELETE":
        try:

            if deep is None:

                objs = Record.objects.filter(drill_id=drill_id)
                res['message'] = "delete all deeps of Drill %s" % drill_id
            else:
                objs = Record.objects.filter(drill_id=drill_id, deep=deep)
                res['message'] = "delete deep %s for Drill %s" % (deep, drill_id)

            num_objs = len(objs)

            if(num_objs == 0):
                res['message'] += ": no record"
                res['status'] = 'fail'
            else:
                objs.delete()
                res['status'] = 'success'

        except Exception as e:
            res['message'] = "Error: " + str(e)
            res['status'] = 'fail'

    elif request.method == "POST":
        try:
            params = request.POST.dict()

            print(params)

            deep = params['deep']
            samplingFreq = params.get('samplingFreq')


            drill = Drill.objects.get(pk=drill_id)
            #print(drill)

            if drill.max_deep.isnumeric() and float(deep) > float(drill.max_deep):
                raise Exception("deep %s exceeds max deep %s" % (deep, drill.max_deep))

            objs = Record.objects.filter(drill_id=drill_id, deep=deep)

            if len(objs) > 0:
                if(samplingFreq is None or samplingFreq == ''):
                    res['message'] = "Error:  deep %s already exists for Drill %s and samplingFreq is null (To update samplingFreq, please provide samplingFreq)" % (deep, drill_id)  # "Error: " + "deep " + deep + ' '
                    res['status'] = 'fail'
                else:
                    assert len(objs) == 2
                    for obj in objs:
                        obj.samplingFreq = samplingFreq
                        obj.save()

                    res['message'] = "update samplingFreq of deep %s for Drill %s (now = %s)" % (
                    deep, drill_id, samplingFreq)  # "Error: " + "deep " + deep + ' '
                    res['status'] = 'success'

            else:
                now = datetime.datetime.now()
                for data_type in ['upWell', 'downWell']:
                    samplingFreq2 = 1 if (samplingFreq is None or samplingFreq == '') else samplingFreq
                    print(samplingFreq2)
                    record = Record(data_type=data_type, drill_id=drill_id, time=now, deep=deep, samplingFreq=samplingFreq2)
                    record.save()

                    logger.info( 'add new deep %s for Drill %s (samplingFreq = %s)' % (deep, drill_id, samplingFreq2))

                res['message'] = 'add deep %s for Drill %s ' % (deep, drill_id)
        except Exception as e:
            res['message'] = "Error: " + str(e)
            res['status'] = 'fail'


    logger.info(res['status'] + ' ' + res['message'])

    return JsonResponse(res)

@csrf_exempt
def record_count(request, drill_id, deep, data_type):
    logger.info(request.method + ' ' + request.path_info)
    res = {
        'data': 0,
        'message': 'record_count',
        'status':  'success',
    }

    if request.method == "GET":
        objs = Record.objects.filter(drill_id=drill_id, deep=deep, data_type=data_type) #.order_by('-time')
        if len(objs) == 0:
            res['data'] = 0
            res['message'] = 'no data'
            res['status'] = 'fail'
        else:
            record_id = objs[0].id
            print('record id is', record_id, deep, data_type)
            try:

                if data_type == 'upWell':
                    cnt = Drill_Upwell_Data.objects.filter(record_id__exact=record_id).count()

                else:
                    cnt = Drill_Downwell_Data.objects.filter(record_id__exact=record_id).count()

                res['data'] = cnt
                res['message'] = '%s pressure cnt: %s' % (data_type, cnt)

            except Exception as e:
                res['message'] = str(e)
                res['status'] = 'fail'

    logger.info(res['status'] + ' ' + res['message'])

    return JsonResponse(res)

@csrf_exempt
def pressure(request, drill_id, deep, data_type):
    print(request, drill_id, deep, data_type)

    if request.method == "DELETE":

        res = {
            'data': None,
            'message': 'delete pressure',
            'status': 'success',
        }
        try:
            objs = Record.objects.filter(drill_id=drill_id, deep=deep, data_type=data_type)
            if len(objs) == 0:
                res['message'] = "Error: no data exist for Drill %s deep %s %s" % (drill_id, deep, data_type)
                res['status'] = 'fail'
                return JsonResponse(res)
            assert len(objs) == 1

            record_id = objs[0].id

            st_sel = int(request.GET['start'])
            et_sel = int(request.GET['end'])

            if data_type == "upWell":
                #objs = Drill_Upwell_Data.objects.filter(record_id__exact=record_id, index__gte=st_sel, index__lt=et_sel)
                objs = Drill_Upwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
            else:
                #objs = Drill_Downwell_Data.objects.filter(record_id__exact=record_id, index__gte=st_sel, index__lt=et_sel)
                objs = Drill_Downwell_Data.objects.filter(record_id__exact=record_id).order_by('index')

            if len(objs) == 0:
                res['message'] = "Warning: no data exist for Drill %s deep %s %s at range [%s,  %s)" % (drill_id, deep, data_type, str(st_sel), str(et_sel))
                res['status'] = 'fail'
                return JsonResponse(res)

            num_objs = len(objs[st_sel:et_sel])

            #print(objs[st_sel:et_sel])
            for obj in objs[st_sel:et_sel]:
                obj.delete()

            res['message'] = 'delete %s pressures' % (num_objs)
        except Exception as e:
            res['message'] = str(e)
            res['status'] = 'fail'

    elif request.method == "GET":
        res = {
            'data': None,
            'message': 'get pressure',
            'status': 'success',
        }

        try:

            assert (deep is not None) and (data_type is not None) and (data_type is not None)

            objs = Record.objects.filter(drill_id=drill_id, deep=deep, data_type=data_type)

            if len(objs) == 0:
                res['message'] = "Error: " + 'no data'
                res['status'] = 'fail'
            else:

                print("1111")
                record_id = objs[0].id
                samplingFreq = int(objs[0].samplingFreq)
                if samplingFreq < 0:
                    samplingFreq = 20

                print('record id is', record_id)

                data = {}

                pageCur = request.GET.get('pageCur')
                pageSize = request.GET.get('pageSize')

                if (pageCur is not None and pageSize is not None):
                    pageCur = int(pageCur)
                    pageSize = int(pageSize)
                    print(pageSize, pageCur)

                if data_type == 'upWell':
                    objs = Drill_Upwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
                    #objs = Drill_Upwell_Data.objects.all()
                    #print(Drill_Upwell_Data.objects.all().count())

                    print(Drill_Upwell_Data.objects.filter(record_id__exact=record_id).count())

                    if (pageCur is not None and pageSize is not None):
                        p = Paginator(objs, pageSize)
                        if (pageCur <= p.num_pages and pageCur > 0):
                            objs = p.page(pageCur).object_list
                        else:
                            objs = []

                    objs = list(objs)
                    objs = [model_to_dict(obj) for obj in objs]

                    axisX = (np.arange(len(objs)))  # + (pageCur - 1) * pageSize).tolist()
                    if (pageCur is not None and pageSize is not None):
                        axisX += (pageCur - 1) * pageSize
                    data['axisX'] = axisX.tolist()

                    fields = ['upStress', 'injectFlow', 'backFlow', 'inject', 'back']
                    print("xxx")
                    for field in fields:

                        raw = [obj[field] for obj in objs]
                        raw = np.array(raw, dtype=np.float16).tolist()


                        if len(raw) <= samplingFreq or samplingFreq <=1:
                            raw_smooth = []
                        else:
                            #raw_smooth = savgol_filter(raw, samplingFreq, 1).tolist()

                            raw_smooth = uniform_filter1d(raw, size=samplingFreq).tolist()

                        data[field] = raw  # [ obj[field] for obj in objs]
                        data[field + '_smooth'] = raw_smooth

                    #print(data)
                    #print(data.keys())

                else:
                    objs = Drill_Downwell_Data.objects.filter(record_id__exact=record_id).order_by('index')

                    print("Number of records : %s" % objs.count())
                    if (pageCur is not None and pageSize is not None):
                        p = Paginator(objs, pageSize)
                        if (pageCur <= p.num_pages and pageCur > 0):
                            objs = p.page(pageCur).object_list
                        else:
                            objs = []


                    objs = list(objs)


                    objs = [model_to_dict(obj) for obj in objs]

                    #objs = [model_to_dict(obj) for obj in objs]


                    axisX = (np.arange(len(objs))) #+ (pageCur - 1) * pageSize).tolist()
                    if (pageCur is not None and pageSize is not None):
                        axisX += (pageCur - 1) * pageSize
                    data['axisX'] = axisX.tolist()

                    fields = ['downStress', 'measureStress', 'downFlow', 'downTemperature']
                    #for field in fields:
                    #    data[field] = [obj[field] for obj in objs]

                    for field in fields:
                        broken = False

                        for obj in objs:
                            if not obj[field].isnumeric():
                                broken = True
                                break

                        raw = [obj[field] for obj in objs]

                        if not broken:
                            raw = np.array(raw, dtype=np.float16).tolist()

                        if len(raw) <= samplingFreq or samplingFreq <=1 or broken:
                            raw_smooth = []
                        else:
                            #raw_smooth = savgol_filter(raw, samplingFreq, 1).tolist()
                            raw_smooth = uniform_filter1d(raw, size=samplingFreq).tolist()

                        data[field] = raw  # [ obj[field] for obj in objs]
                        data[field + '_smooth'] = raw_smooth

                res['data'] = data
                #res['message'] = 'get'

        except Exception as e:
                res['message'] = "Error: " + str(e)
                res['status'] = 'fail'


    return JsonResponse(res)

def get_pressure(drill_id, deep, data_type):

    objs = Record.objects.filter(drill_id=drill_id, deep=deep, data_type=data_type) #.order_by('-time')

    if len(objs) == 0:
        return None
    else:
        record_id = objs[0].id
        samplingFreq = objs[0].samplingFreq
    pressure = []
    print(samplingFreq)
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
        return pressure, int(samplingFreq)
    else:
        return None


@csrf_exempt
def calculate_pb(request, drill_id, deep, data_type):
    now0 = time.time()
    logger.info(request.method + ' ' + request.path_info)
    print(request, drill_id, deep, data_type)
    res = {
        'data': None,
        'message': 'calculate_pb',
        'status': 'success',
    }
    st_sel = int(request.GET['start'])
    et_sel = int(request.GET['end'])

    now1 = time.time()

    ret = get_pressure(drill_id, deep, data_type)
    if ret is None:
        res['message'] = 'no data'
        res['status'] = 'fail'
        return JsonResponse(res)
    pressure, samplingFreq = ret

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
def calculate_pr(request, drill_id, deep, data_type):
    logger.info(request.method + ' ' + request.path_info)
    res = {
        'data': None,
        'message': 'calculate_pb',
        'status': 'success',
    }

    st_sel = int(request.GET['start'])
    et_sel = int(request.GET['end'])

    ret = get_pressure(drill_id, deep, data_type)
    if ret is None:
        res['message'] = 'no data'
        res['status'] = 'fail'
        return JsonResponse(res)
    pressure, samplingFreq = ret

    est = estimate_pr(pressure, st_sel, et_sel, samplingFreq=samplingFreq)
    if est is None:
        res['message'] = 'error in estimate_pr'
        res['status'] = 'fail'

        return JsonResponse(res)

    res['data'] = est

    logger.info(res['status'] + ' ' + res['message'])
    return JsonResponse(res)



@csrf_exempt
def calculate_ps(request, drill_id, deep, data_type):
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

    ret = get_pressure(drill_id, deep, data_type)
    if ret is None:
        res['message'] = 'no data'
        res['status'] = 'fail'
        return JsonResponse(res)
    pressure, samplingFreq = ret

    if method == 1:
        est = estimate_ps_tangent(pressure, st_sel, et_sel, samplingFreq=samplingFreq)
    elif method == 2:
        est = estimate_ps_muskat(pressure, st_sel, et_sel, samplingFreq=samplingFreq)
    elif method == 3:
        est = estimate_ps_dp_dt_robust(pressure, st_sel, et_sel, samplingFreq=samplingFreq)
    elif method == 4:
        est = estimate_ps_dt_dp_robust(pressure, st_sel, et_sel, samplingFreq=samplingFreq)

    if est is None:
        res['status'] = 'fail'
        res['message'] = 'error in estimate_ps'
        return JsonResponse(res)

    res['data'] = est

    logger.info(res['status'] + ' ' + res['message'])

    return JsonResponse(res)
