from django.contrib import admin

# Register your models here.
from .models import Drill, Drill_Upwell_Data, Drill_Downwell_Data, Record, Calculation

admin.site.register(Drill)
admin.site.register(Drill_Upwell_Data)
admin.site.register(Drill_Downwell_Data)
admin.site.register(Record)
admin.site.register(Calculation)