from django.db import models
from uberclock.tools import ez_chronos
import struct
# Create your models here.



class Entry(models.Model):
    date = models.DateTimeField("Date", null=False, auto_now_add=True)
    value = models.IntegerField(max_length=10, null=False)
    counter = models.IntegerField(max_length=3, null=True)

    def __repr__(self):
        return "<Entry %s %d>" %(self.date, self.value)

class DBWriter(ez_chronos.CommandDispatcher):

    def smpl_0x01(self, data):
        # acceleration data
        data = self.get_smpl_data(data)
        print "x: %3d y: %3d z: %3d" %(ord(data[0]), ord(data[1]), ord(data[2]))

    # ppt buttons
    #UP
    def smpl_0x32(self, data):
        # acceleration data
        print "UP pressed"
    #STAR
    def smpl_0x12(self, data):
        # acceleration data
        print "STAR pressed"
    #SHARP
    def smpl_0x22(self, data):
        # acceleration data
        print "SHARP pressed"

    def smpl_0x03(self, data):
        # acceleration data
        mdata = self.get_smpl_data(data)
        var = struct.unpack('H', mdata[:2])[0]
        counter = ord(mdata[2])
        print "%3d %6d %s" %(counter, var, "#"*max(min((var/500), 80),1))
        entry = Entry(value=var, counter=counter)
        entry.save()
