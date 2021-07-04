from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    path('drill/<int:drill_id>', views.drill, name='drill'),
    path('drill', views.drill, name='drill'),
    path('drill/<int:drill_id>/<str:data_type>/csv', views.fileUpload, name='drill'), #POST "/drill/{id}/upWell/csv" csv/xlsx文件

    path('drill/<int:drill_id>/<str:data_type>/<int:record_id>', views.record, name='drill'), #DELETE“/drill/{id}/upWell/{id}” 删除id的数据
                                                                                              #DELETE“/drill/{id}/downWell/{id}” 删除id的数据
    #path("/drill/<int:drill_id>/<str:data_type>", views.record, name='drill')


    #GET "/drill/{id}/upWell/{id}/ps?method=[method]&start={st}&end={ed}"

    path('drill/<int:drill_id>/<str:data_type>/<int:record_id>/pb', views.calculate_pb, name='drill'),

    path('drill/<int:drill_id>/<str:data_type>/<int:record_id>/pr', views.calculate_pr, name='drill'),
]