from django.db import models
import datetime
# Create your models here.

import logging

# 实例化logging对象,并以当前文件的名字作为logger实例的名字
logger = logging.getLogger(__name__)
# 生成一个名字叫做 collect 的日志实例
logger_c = logging.getLogger('file')


class Drill(models.Model):
    """Model representing a book (but not a specific copy of a book)."""

    name = models.CharField(max_length=50, default='')


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

    max_deep = models.CharField(max_length=50, default='')

    comment = models.CharField(max_length=50, default='')

    def __str__(self):
        """String for representing the Model object."""
        return self.name

    def save(self, *args, **kwargs):
        super(Drill, self).save(*args, **kwargs)
        
        now = datetime.datetime.now()
        for data_type in ['upWell', 'downWell']:

            record = Record(data_type=data_type, drill_id=self.id, time=now, deep=self.max_deep, samplingFreq=1)
            record.save()

            logger.info('add new deep %s for Drill %s' % (self.max_deep, self.id))



class Record(models.Model):

    time = models.TimeField(auto_now=False, auto_now_add=False)  # 采集时间
    data_type = models.CharField(max_length=20)
    deep = models.CharField(max_length=50, default='')
    samplingFreq = models.CharField(max_length=50, default='')

    drill = models.ForeignKey('Drill', on_delete=models.CASCADE)

class Calculation(models.Model):

    # 记录下区间起点终点，结果，计算时间、所在drill

    stress = models.CharField(max_length=20)

    stress_type = models.CharField(max_length=20)  # pb, pr, ps

    method = models.CharField(max_length=20)  # 1,2,3,4


    time = models.DateTimeField(auto_now=False, auto_now_add=False)  # 采集时间

    start = models.CharField(max_length=20)
    end = models.CharField(max_length=20)

    record = models.ForeignKey('Record', on_delete=models.CASCADE)





class Drill_Upwell_Data(models.Model):

    index   = models.IntegerField()
    upStress = models.CharField(max_length=50, default='')   # 井上压力值（MPa）
    injectFlow = models.CharField(max_length=50, default='') # 注入流量值（L/min）
    backFlow = models.CharField(max_length=50, default='')   # 回水流量值（L/min）

    inject = models.CharField(max_length=50, default='')      # 注入量（L/min）
    back = models.CharField(max_length=50, default='')      # 回流量（L/min)
    record = models.ForeignKey('Record', on_delete=models.CASCADE)


    def __str__(self):
        """String for representing the Model object."""
        return str(self.index)

class Drill_Downwell_Data(models.Model):

    #time = models.TimeField(auto_now=False, auto_now_add=False)        # 采集时间

    index = models.IntegerField()
    downStress = models.CharField(max_length=50, default='')
    measureStress = models.CharField(max_length=50, default='')
    downFlow = models.CharField(max_length=50, default='')
    downTemperature = models.CharField(max_length=50, default='')


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