from django.shortcuts import render
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import Drill, Drill_Upwell_Data, Drill_Downwell_Data, Record

from django.core import serializers
from django.core.paginator import Paginator

from django.http import HttpResponse


import os, datetime

from django.forms.models import model_to_dict

from .utils import save_downWell, save_upWell
from .calculate import estimate_pb, estimate_pr_tangent, estimate_pr_muskat

import json
# Create your views here.
def index(request):
    x = {}
    x["a"] = 1
    x["b"] = 1
    x["c"] = 1
    return JsonResponse(x)


@csrf_exempt
def drill(request, drill_id=None):


    if request.method == 'GET':

        print(request.GET)
        print(request.path)

        objs = []
        if drill_id is not None:  # GET "/drill/{id}" 获得id的钻孔
            print(drill_id)
            obj = Drill.objects.get(pk=drill_id)

            objs.append(obj)


        else:   #GET "/drill?pageCur=1&pageSize=10" 获得所有数据（第pageCur页，每页pageSize个，页号从1开始），返回list

            pageCur = request.GET['pageCur']
            pageSize = request.GET['pageSize']

            objs_all = Drill.objects.all()

            p = Paginator(objs_all, pageSize)
            objs = p.page(pageCur).object_list





        serialized_obj = serializers.serialize('json', objs)
        objs = json.loads(serialized_obj)

        for obj in objs:
            obj['fields']['id'] = obj['pk']

        serialized_obj = json.dumps(objs)

        print(serialized_obj)

        return HttpResponse(serialized_obj, content_type='application/json')


        #return JsonResponse(serialized_obj)
        #print(serialized_obj)
        #print()

    if request.method == 'POST':
        params = request.POST.dict()
        print(params)

        params.pop('id', None)
        obj = Drill(**params)

        obj.save()



    elif request.method == 'DELETE':
        print(drill_id)

        obj = Drill.objects.get(pk=drill_id)

        obj.delete()

        print(obj)
        #question = get_object_or_404(Drill, pk=id)

    elif request.method == 'PUT':

        try:
            obj = Drill.objects.get(pk=drill_id)

            params =  request.PUT.dict()
            for k, v in params:
                setattr(obj, k, v)

            obj.save()
        except:
            pass


    return  JsonResponse({'status':'good'})



@csrf_exempt
def fileUpload(request, drill_id, data_type):
    #print(drill_id, data_type)

    #删除旧数据
    # if data_type == "upWell":
    #     res = Drill_Upwell_Data.objects.filter(drill_id__exact=drill_id)
    #     print(len(res))
    #
    #     res.delete()
    # else:
    #     res = Drill_Downwell_Data.objects.filter(drill_id__exact=drill_id)
    #     print(len(res))
    #
    #     res.delete()
    #return JsonResponse({'status': 'good'})

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
            save_upWell(filename, record.id)
        else:
            save_downWell(filename, record.id)

    return JsonResponse({'status':'good'})


@csrf_exempt
def record(request, drill_id, data_type, record_id=None):
    res = {
        'data': None,
        'message': 'record',
        'status':  'success',
    }

    if request.method == "DELETE":
        try:
            Record.objects.get(pk=record_id).delete()

            res['message'] = 'delete'

        except Exception as e:
            res['message'] = str(e)
            res['status'] = 'fail'

    elif request.method == "GET":
        try:
            data = {}
            if data_type == 'upWell':
                objs = Drill_Upwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
                objs = [model_to_dict(obj) for obj in objs]

                data['axisX'] = list(range(len(objs)))
                fields = ['upStress', 'injectFlow', 'backFlow', 'inject', 'back']
                for field in fields:
                    data[field] = [ obj[field] for obj in objs]

                print(data)
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
            res['status']  = 'fail'

    #contact_list = Contact.objects.all()
    #paginator = Paginator(contact_list, 25)  # Show 25 contacts per page.

    return JsonResponse(res)

#GET "/drill/{id}/upWell/{id}/pb?start={st}&end={ed}"
@csrf_exempt
def calculate_pb(request, drill_id, data_type, record_id):
    res = {
        'data': None,
        'message': 'calculate_pb',
        'status': 'success',
    }

    if request.method == "GET":
        st_sel = int(request.GET['start'])
        et_sel = int(request.GET['end'])

        pressure = []
        if data_type == "upWell":
            objs = Drill_Upwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
            pressure = [obj.upStress for obj in objs]
        else:
            objs = Drill_Downwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
            pressure = [obj.downStress for obj in objs]

        est = estimate_pb(pressure, st_sel, et_sel)
        if est is None:
            res['status'] = 'fail'
            res['message'] = 'pr calculation'
            return JsonResponse(res)

        res['data'] = est

    return JsonResponse(res)


@csrf_exempt
def calculate_pr(request, drill_id, data_type, record_id):
    print(request, drill_id, data_type, record_id)
    res = {
        'data': None,
        'message': 'good',
        'status': 'success',
    }

    if request.method == "GET":
        st_sel = int(request.GET['start'])
        et_sel = int(request.GET['end'])

        method = int(request.GET['method'])

        pressure = []
        if data_type == "upWell":
            objs = Drill_Upwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
            pressure = [obj.upStress for obj in objs]
        else:
            objs = Drill_Downwell_Data.objects.filter(record_id__exact=record_id).order_by('index')
            pressure = [obj.downStress for obj in objs]

        if method == 1:
            est = estimate_pr_tangent(pressure, st_sel, et_sel)
        elif method == 2:
            est = estimate_pr_muskat(pressure, st_sel, et_sel)

        if est is None:
            res['status'] = 'fail'
            res['message'] = 'pr calculation'
            return JsonResponse(res)

        res['data'] = est

    return JsonResponse(res)
