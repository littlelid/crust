from django.db import models
import datetime
# Create your models here.

class Drill(models.Model):
    """Model representing a book (but not a specific copy of a book)."""

    name = models.CharField(max_length=50, default='')

    deep = models.CharField(max_length=50, default='')
    position = models.CharField(max_length=50, default='')

    rockAvgCapacity = models.CharField(max_length=50, default='')
    liquidCapacity = models.CharField(max_length=50, default='')
    longitude = models.CharField(max_length=50, default='')
    latitude = models.CharField(max_length=50, default='')
    staticWaterLevel = models.CharField(max_length=50, default='')
    measureBackground = models.CharField(max_length=50, default='')
    measureUnit = models.CharField(max_length=50, default='')
    measurePrincipal = models.CharField(max_length=50, default='')

    measureDate = models.DateField(default=datetime.date.today)

    comment = models.CharField(max_length=50, default='')


    def __str__(self):
        """String for representing the Model object."""
        return self.name

class Record(models.Model):

    time = models.TimeField(auto_now=False, auto_now_add=False)  # 采集时间
    data_type = models.CharField(max_length=20)
    drill = models.ForeignKey('Drill', on_delete=models.CASCADE)


class Drill_Upwell_Data(models.Model):

    index   = models.IntegerField()
    upStress = models.FloatField()   # 井上压力值（MPa）
    injectFlow = models.FloatField() # 注入流量值（L/min）
    backFlow = models.FloatField()   # 回水流量值（L/min）

    inject = models.FloatField()       # 注入量（L/min）
    back = models.FloatField()       # 回流量（L/min)
    record = models.ForeignKey('Record', on_delete=models.CASCADE)



    def __str__(self):
        """String for representing the Model object."""
        return str(self.index)

class Drill_Downwell_Data(models.Model):

    #time = models.TimeField(auto_now=False, auto_now_add=False)        # 采集时间

    index   = models.IntegerField()
    downStress = models.FloatField()
    measureStress = models.FloatField()
    downFlow = models.FloatField()
    downTemperature = models.FloatField()


    record = models.ForeignKey('Record', on_delete=models.CASCADE)

    def __str__(self):
        """String for representing the Model object."""
        return str(self.index)

'''   
name,
deep,
postion,
rockAvgCapacity,
liquidCapacity,
longitude,
latitude,
staticWaterLevel,
measureBackground,
measureUnit,
measurePrincipal,
measureDate,
comment
'''