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
import traceback
import os, datetime
import numpy as np
from django.forms.models import model_to_dict

from .utils import save_downWell, save_upWell, isfloat
from .calculate import estimate_pb, estimate_pr, estimate_ps_tangent, estimate_ps_muskat, estimate_ps_dp_dt, estimate_ps_dt_dp, estimate_ps_dp_dt_robust, estimate_ps_dt_dp_robust, fit_main_force, fit_S_H_div_S_v, fit_S_H_div_S_h


from scipy.ndimage.filters import uniform_filter1d
from sklearn.linear_model import HuberRegressor

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
            samplingFreqs = {}
            for record in records: #每个upWell 和 downWell都有一个record
                if record.deep not in samplingFreqs:
                    samplingFreqs[record.deep]={}
                samplingFreqs[record.deep][record.data_type] = record.samplingFreq

            #samplingFreqs = [ record.samplingFreq for record in records]
            deeps = list(samplingFreqs.keys())
            idxs = np.argsort([float(deep) for deep in deeps])
            deeps = [ deeps[idx] for idx in idxs]
            samplingFreqs = [samplingFreqs[deep] for deep in deeps]

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

            if stress_type == "all":
                data = {}
                for t in ['pb', 'pr', 'ps']:

                    if t is 'ps':
                        methods = [1, 2, 3, 4]
                    else:
                        methods = [1]

                    data[t] = []
                    for method in methods:
                        objs = Calculation.objects.filter(record_id__exact=record_id, stress_type=t,
                                                          method=method).order_by('-time')

                        if len(objs) >= 1:
                            objs = objs[0:1]

                        serialized_obj = serializers.serialize('json', objs)
                        objs = json.loads(serialized_obj)

                        for obj in objs:
                            obj['fields']['id'] = obj['pk']

                        data[t].extend(objs)

                res['data'] = data
                res['message'] = "get all calculations"
                res['status'] = 'success' if len(objs) > 0 else 'fail'

            else:
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
            data_type = params.get('data_type')

            drill = Drill.objects.get(pk=drill_id)
            #print(drill)

            if drill.max_deep.isnumeric() and float(deep) > float(drill.max_deep):
                raise Exception("deep %s exceeds max deep %s" % (deep, drill.max_deep))

            objs = Record.objects.filter(drill_id=drill_id, deep=deep)

            if len(objs) > 0:   # update drill
                if(samplingFreq is None or samplingFreq == ''):
                    raise Exception( "Error:  deep %s already exists for Drill %s and samplingFreq is null (To update samplingFreq, please provide samplingFreq)" % (deep, drill_id))
                    #res['message'] = "Error:  deep %s already exists for Drill %s and samplingFreq is null (To update samplingFreq, please provide samplingFreq)" % (deep, drill_id)  # "Error: " + "deep " + deep + ' '
                    #res['status'] = 'fail'
                else:
                    assert len(objs) == 2, "Multiple Records for deep %s." % deep
                    for obj in objs:
                        if data_type is None or obj.data_type == data_type:
                            obj.samplingFreq = samplingFreq
                            obj.save()

                    res['message'] = "update samplingFreq of deep %s for Drill %s %s (now = %s)" % (deep, drill_id, data_type, samplingFreq)  # "Error: " + "deep " + deep + ' '
                    res['status'] = 'success'

            else:  # add deep
                now = datetime.datetime.now()
                for data_type in ['upWell', 'downWell']:
                    samplingFreq2 = 20 if (samplingFreq is None or samplingFreq == '') else samplingFreq
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

                    for field in fields:
                        broken = False

                        for obj in objs:
                            if not isfloat(obj[field]):
                                broken = True
                                break

                        raw = [obj[field] for obj in objs]

                        if not broken:
                            raw = np.array(raw, dtype=np.float16).tolist()

                        if len(raw) <= samplingFreq or samplingFreq <= 1 or broken:
                            raw_smooth = []
                        else:
                            # raw_smooth = savgol_filter(raw, samplingFreq, 1).tolist()
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
                            if not isfloat(obj[field]):
                                print(obj[field])
                                broken = True
                                break

                        raw = [obj[field] for obj in objs]

                        if not broken:
                            raw = np.array(raw, dtype=np.float16).tolist()

                        if len(raw) <= samplingFreq or samplingFreq <=1 or broken:
                            print(field, "Skip Smooth")
                            raw_smooth = []
                        else:
                            #raw_smooth = savgol_filter(raw, samplingFreq, 1).tolist()
                            raw_smooth = uniform_filter1d(raw, size=samplingFreq).tolist()

                        data[field] = raw  # [ obj[field] for obj in objs]
                        data[field + '_smooth'] = raw_smooth

                res['data'] = data
                #res['message'] = 'get'

        except Exception as e:
                traceback.print_exc()
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


def calculate_main_force(request, drill_id, data_type):
    logger.info(request.method + ' ' + request.path_info)
    res = {
        'data': None,
        'message': 'main force',
        'status':  'success',
    }


    try:
        drills = Drill.objects.filter(pk=drill_id)
        if len(drills) == 0:
            raise Exception("Drill %s not exists" % drill_id)
        drill = drills[0]

        rockAvgCapacity = 26.5 if not isfloat(drill.rockAvgCapacity) else float(drill.rockAvgCapacity)
        liquidCapacity  = 10 if not isfloat(drill.liquidCapacity) else float(drill.liquidCapacity)
        staticWaterLevel = float(drill.staticWaterLevel)
        print(rockAvgCapacity, liquidCapacity, staticWaterLevel)
        records = Record.objects.filter(drill_id=drill_id, data_type=data_type)

        S_Hs = []
        S_hs = []

        S_H_div_S_h = []
        S_H_div_S_v = []

        deeps_S_H = []
        deeps_S_h = []

        deeps_S_H_div_S_h = []
        deeps_S_H_div_S_v = []


        tables = []
        for record in records:
            deep = float(record.deep)

            P_H = 0.001 * deep * liquidCapacity

            P_0 = 0.001 * (deep - staticWaterLevel) * liquidCapacity
            if P_0 <= 0:
                P_0 = 0

            S_v = 0.001 * rockAvgCapacity * deep

            P_r = None
            P_r_objs = Calculation.objects.filter(record_id__exact=record.id, stress_type="pr", method=1).order_by('-time')
            if len(P_r_objs) > 0 and  isfloat(P_r_objs[0].stress):
                P_r = float(P_r_objs[0].stress)

            P_b = None
            P_b_objs = Calculation.objects.filter(record_id__exact=record.id, stress_type="pb", method=1).order_by('-time')
            if len(P_b_objs) > 0 and isfloat(P_b_objs[0].stress):
                P_b = float(P_b_objs[0].stress)

            P_s = None
            P_s_list = []
            for method in [1, 2, 3, 4]:
                P_s_objs = Calculation.objects.filter(record_id__exact=record.id, stress_type="ps", method=method).order_by('-time')
                if len(P_r_objs) > 0 and isfloat(P_s_objs[0].stress):
                    P_s_list.append(float(P_s_objs[0].stress))
            if len(P_s_list) > 0:
                P_s = np.mean(P_s_list)

            T = None
            if (P_b is not None) and (P_r is not None):
                T = P_b - P_r

            S_H = None
            if (P_r is not None) and (P_s is not None):
                print(P_s, P_r, P_0)
                S_H = 3 * P_s - P_r - P_0

                deeps_S_H.append(deep)
                S_Hs.append(S_H)

            S_h = None
            if (P_s is not None):
                S_h = P_s

                deeps_S_h.append(deep)
                S_hs.append(S_h)

            #deeps_S_H_div_S_h = []
            #deeps_S_H_div_S_v = []
            if (S_H is not None) and (S_h is not None):
                deeps_S_H_div_S_h.append(deep)
                S_H_div_S_h.append(S_H / (S_h + 1e-5))

            if (S_H is not None) and (S_v is not None):
                deeps_S_H_div_S_v.append(deep)
                S_H_div_S_v.append(S_H / (S_v + 1e-5))

            tables.append(
                {
                    "deep": deep,
                    "P_H":  P_H,
                    "P_0":  P_0,
                    "P_b":  P_b,
                    "P_r":  P_r,
                    "P_s":  P_s,
                    "T":    T,
                    "S_H":  S_H,
                    "S_h":  S_h,
                    "S_v":  S_v,
                }
            )

        #
        # deeps_S_H =  [
        #     71.8,
        #     93.8,
        #     127.8,
        #     151.4,
        #     168.9,
        # ]
        #
        # S_Hs = [2.3775,
        #                 3.03,
        #                 2.415,
        #                 3.4875,
        #                 3.6475,]


        k_S_H, b_S_H, X_S_H, y_S_H = fit_main_force(deeps_S_H, S_Hs)
        k_S_h, b_S_h, X_S_h, y_S_h = fit_main_force(deeps_S_h, S_hs)

        lines_main_force = [
            {
                "name": "S_H",
                "type": "scatter",
                "markerType": "circle",
                "showInLegend": True,
                "dataPoints": {'x': deeps_S_H, 'y': S_Hs},
            },
            {
                "name": "S_h",
                "type": "scatter",
                "markerType": "circle",
                "showInLegend": True,
                "dataPoints": {'x': deeps_S_h, 'y': S_hs},
            },
            {
                "name": "S_H = %sH + %s" % (np.round(k_S_H, 4), np.round(b_S_H, 4)),
                "type": "line",
                "showInLegend": True,
                "dataPoints": {'x': X_S_H, 'y': y_S_H},
            },
            {
                "name": "S_h = %sH + %s" % (np.round(k_S_h,4), np.round(b_S_h) ),
                "type": "line",
                "showInLegend": True,
                "dataPoints": {'x': X_S_h, 'y': y_S_h},
            },
            #{
            #    "name": "the third stage",
            #    "type": "line",
            #    "showInLegend": True,
            #    "dataPoints": {"x": X1_plot.tolist(), "y": y1_plot.tolist()},
            #},
        ]

        k_S_H_div_S_v, b_S_H_div_S_v, X_S_H_div_S_v, y_S_H_div_S_v = fit_S_H_div_S_v(deeps_S_H_div_S_v, S_H_div_S_v)

        lines_K_HV = [
            {
                "name": "K_HV",
                "type": "scatter",
                "markerType": "circle",
                "showInLegend": True,
                "dataPoints": {'x': deeps_S_H_div_S_v, 'y': S_H_div_S_v},
            },
            {
                "name": "K_HV = %s/H + %s" % (np.round(k_S_H_div_S_v,4), np.round(b_S_H_div_S_v,4) ),
                "type": "line",
                "showInLegend": True,
                "dataPoints": {'x': X_S_H_div_S_v, 'y': y_S_H_div_S_v},
            },
        ]

        k_S_H_div_S_h, b_S_H_div_S_h, X_S_H_div_S_h, y_S_H_div_S_h = fit_S_H_div_S_h(deeps_S_H_div_S_h, S_H_div_S_h)

        lines_K_Hh = [
            {
                "name": "K_Hh",
                "type": "scatter",
                "markerType": "circle",
                "showInLegend": True,
                "dataPoints": {'x': deeps_S_H_div_S_h, 'y': S_H_div_S_h},
            },
            {
                "name": "K_Hh = %sH + %s" % (np.round(k_S_H_div_S_h,4), np.round(b_S_H_div_S_h,4) ),
                "type": "line",
                "showInLegend": True,
                "dataPoints": {'x': X_S_H_div_S_h, 'y': y_S_H_div_S_h},
            },
        ]

        # print(np.array(X_S_H)*k_S_H + b_S_H)
        # print(k_S_H, b_S_H, X_S_H, y_S_H)


        res['data'] = {
            "lines_main_force": lines_main_force,
            "lines_K_HV": lines_K_HV,
            "lines_K_Hh": lines_K_Hh,
            "table": tables
        }

    except Exception as e:
        traceback.print_exc()
        res['message'] = "Error: " + str(e)
        res['status'] = 'fail'

    return JsonResponse(res)
