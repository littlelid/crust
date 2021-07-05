from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),



    path('drill/<int:drill_id>', views.drill, name='drill'),
    path('drill', views.drill, name='drill'),
    path('drill/', views.drill, name='drill'),


    path('drill/<int:drill_id>/<str:data_type>/csv', views.fileUpload, name='fileupload'), #POST "/drill/{id}/upWell/csv" csv/xlsx文件


    #path('drill/<int:drill_id>/<str:data_type>/<int:record_id>', views.record, name='record'),
    path('drill/<int:drill_id>/<str:data_type>', views.record, name='record'),

    #GET "/drill/{id}/upWell/ps?method=[method]&start={st}&end={ed}"
    path('drill/<int:drill_id>/<str:data_type>/pb', views.calculate_pb, name='calculate_pb'),
    #GET "/drill/{id}/upWell/pr?method=[method]&start={st}&end={ed}"
    path('drill/<int:drill_id>/<str:data_type>/pr', views.calculate_pr, name='calculate_pr'),

]

