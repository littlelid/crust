from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),



    path('drill/<int:drill_id>', views.drill, name='drill'),
    path('drill', views.drill, name='drill'),
    path('drill/', views.drill, name='drill'),




    path('drill/<int:drill_id>/<str:deep>/<str:data_type>/csv', views.fileUpload, name='fileupload'), #POST "/drill/{id}/upWell/csv" csv/xlsx文件


    path('drill/<int:drill_id>/<str:deep>/<str:data_type>/save', views.calculation, name='calculation'),


    path('drill/<int:drill_id>/record', views.record, name='record'),
    path('drill/<int:drill_id>/<str:deep>/record', views.record, name='record'),
    path('drill/<int:drill_id>/<str:deep>/<str:data_type>/record', views.record, name='record'),

    path('drill/<int:drill_id>/<str:deep>/<str:data_type>/record_count', views.record_count, name='record_count'),

    path('drill/<int:drill_id>/<str:deep>/<str:data_type>/pressure', views.pressure, name='pressure'),
    path('drill/<int:drill_id>/<str:deep>/<str:data_type>/pressure/<str:action>', views.pressure, name='pressure'),

    # GET "/drill/{id}/upWell/pb?&start={st}&end={ed}"
    path('drill/<int:drill_id>/<str:deep>/<str:data_type>/pb', views.calculate_pb, name='calculate_pr'),

    #GET "/drill/{id}/upWell/pr?&start={st}&end={ed}"
    path('drill/<int:drill_id>/<str:deep>/<str:data_type>/pr', views.calculate_pr, name='calculate_pr'),

    #GET "/drill/{id}/upWell/pr?method=[method]&start={st}&end={ed}"
    path('drill/<int:drill_id>/<str:deep>/<str:data_type>/ps', views.calculate_ps, name='calculate_ps'),


    path('drill/<int:drill_id>/<str:data_type>/main_force', views.calculate_main_force, name='calculate_main_force'),



    path('drill/count', views.drill_count, name='drill_count'),

]

