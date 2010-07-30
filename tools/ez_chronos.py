import serial
import array
import sys
import struct
import logging
from time import sleep

def msleep(msec):
    sleep(0.001*msec)

def splitIntoNPieces(s,n):
    return [s[i:i+n] for i in range(0, len(s), n)]

log = logging.getLogger("ez_chronos")

# // Command codes
BM_GET_STATUS =             0x00
BM_GET_PRODUCT_ID =         0x20

# BlueRobin
BM_RESET =                  0x01
BM_START_BLUEROBIN =        0x02
BM_SET_BLUEROBIN_ID =       0x03
BM_GET_BLUEROBIN_ID =       0x04
BM_SET_HEARTRATE =          0x05    
BM_STOP_BLUEROBIN =         0x06
BM_SET_SPEED =              0x0A
#
# // Simpliciti
BM_SIMPLICITI_DATA =        0x06
BM_START_SIMPLICITI =       0x07
BM_GET_SIMPLICITIDATA =     0x08
BM_STOP_SIMPLICITI =        0x09

SIMPLICITI_NO_DATA =        0xFF
SIMPLICITI_DATA_OFFSET =       3
#
# // Sync
BM_SYNC_START =             0x30
BM_SYNC_SEND_COMMAND =      0x31
BM_SYNC_GET_BUFFER_STATUS = 0x32
BM_SYNC_READ_BUFFER	=       0x33
#
# //Wireless BSL
BM_START_WBSL =             0x40
BM_GET_WBSL_STATUS =        0x41
BM_INIT_OK_WBSL =           0x42
BM_INIT_INVALID_WBSL =      0x43
BM_TRANSFER_OK_WBSL =       0x44
BM_TRANSFER_INVALID_WBSL =  0x45
BM_STOP_WBSL =              0x46
BM_SEND_DATA_WBSL =         0x47
BM_GET_PACKET_STATUS_WBSL = 0x48
BM_GET_MAX_PAYLOAD_WBSL =   0x49
#
# // Test
BM_INIT_TEST =              0x70
BM_NEXT_TEST =              0x71
BM_WRITE_BYTE =             0x72
BM_GET_TEST_RESULT =        0x73
#
# // System states  
HW_IDLE =                        0x00
HW_SIMPLICITI_STOPPED =          0x01
HW_SIMPLICITI_TRYING_TO_LINK =   0x02
HW_SIMPLICITI_LINKED =           0x03
HW_BLUEROBIN_STOPPED =           0x04
HW_BLUEROBIN_TRANSMITTING =      0x05
HW_ERROR =                       0x05
HW_NO_ERROR =                    0x06
HW_NOT_CONNECTED =               0x07
HW_SIMPLICITI_LINK_TIMEOUT =     0x08
HW_WBSL_TRYING_TO_LINK =         0x09
HW_WBSL_LINKED =                 0x0A
HW_WBSL_ERROR =                  0x0B
HW_WBSL_STOPPED =                0x0C
HW_WBSL_LINK_TIMEOUT =           0x0D

BM_SYNC_DATA_LENGTH  =           19

SYNC_AP_CMD_NOOP =               0x01
SYNC_DATA_SENT =                 0x55

SYNC_AP_CMD_NOP                       = 0x01
SYNC_AP_CMD_GET_STATUS                = 0x02
SYNC_AP_CMD_SET_WATCH                 = 0x03
SYNC_AP_CMD_GET_MEMORY_BLOCKS_MODE_1  = 0x04
SYNC_AP_CMD_GET_MEMORY_BLOCKS_MODE_2  = 0x05
SYNC_AP_CMD_ERASE_MEMORY              = 0x06
SYNC_AP_CMD_EXIT                      = 0x07

class Simpliciti(object):
    """
    Connection class for interaction with a CC1111 dongle
    """
    # doc see BM_API.h in access point sources


    PREAMBLE = 0xFF
    BROADCAST = [ 0xFF, 0xFF, 0xFF, 0xFF ]

    def __init__(self, stream):
        self.stream = stream
        self.rbuffer = ""
        self.autosync = True
        self.last_cmd = ()
        #self._nullread()
        self.debug = False
        self.sync()
        #self.send_smpl_data([], wait=False)
    #def 

    #def _nullread(self):
    #    self.stream.read()

    @staticmethod
    def dstr(data):
        if not data:
            return ""
        rv = ""
        for x in data:
            rv += "\\x%02x" %ord(x)
        return rv

    def close(self):
        """
        Shut down gracefully
        """
        self.stop_ap()
        self.stream.close()
        self.stream = None

    def send(self, cmd_, data=None):
        ln = 3
        # // Packet bytes
        # //
        # // Byte 0	        Start marker (0xFF)
        #PACKET_BYTE_START          (0u)
        # // Byte 1	        Command code
        #PACKET_BYTE_CMD            (1u)
        # // Byte 2	        Packet size (including overhead)
        #PACKET_BYTE_SIZE           (2u)
        # // Byte 3..packet_size  Data
        #PACKET_BYTE_FIRST_DATA     (3u)
        assert isinstance(cmd_, int)
        assert cmd_ < 256

        if isinstance(data, str):
            assert len(data) < 252
            ln = 3+len(data)
            res = array.array('B', [0xFF, cmd_, ln])
            res.fromlist([ord(x) for x in data])
        elif isinstance(data, list):
            assert len(data) < 252
            ln = 3+len(data)
            res = array.array('B', [0xFF, cmd_, ln] + data)
        else:
            res = array.array('B', [0xFF, cmd_, ln])
        self.last_cmd = (cmd_, ln)
        if self.debug:
            if self.debug >= 3:
                print "send:" + self.dstr(res.tostring())
            else:
                if res.tostring() not in ('\xff\x08\x07\x00\x00\x00\x00', '\xff\x32\x04\x00'):
                    print "send:" + self.dstr(res.tostring())
        self.stream.write(res.tostring())
        msleep(15)
        return ln

    def sync(self):
        self.last_cmd = ()
        print "waiting", self.stream.inWaiting()
        self.stop_ap()
        #self.stream.read()
        for i in xrange(10):
            res = self.send_read(BM_GET_STATUS, [0x00])
            res = self.send_read(BM_RESET, [])
            #self.stream.read()

    def read(self, ln=None):
        offset = 0
        self.rbuffer += self.stream.read(ln or self.last_cmd[1])
        
        if len(self.rbuffer) < 2:
            raise ValueError, "Not enough bytes returned. Buffer: %s" %len(self.rbuffer)
        if ord(self.rbuffer[0]) != 0xFF:
            if not self.autosync:
                raise Warning, "Desync detected"
            for i in xrange(len(self.rbuffer)):
                if ord(self.rbuffer[i]) == 0xFF:
                    log.info("offset detected %s" %i)
                    if len(self.rbuffer) >= i+2 and \
                       ord(self.rbuffer[i+1]) == self.last_cmd[0] and \
                       ord(self.rbuffer[i+2]) == self.last_cmd[1]:
                        offset = i
                        break
            else:
                raise ValueError, "can't find start pattern"
                if self.autosync:
                    self.rbuffer = ""
                    self.sync()
        res = self.rbuffer[offset:ord(self.rbuffer[offset+2])]
        self.rbuffer = self.rbuffer[ord(self.rbuffer[offset+2]):]
        return res

    def send_read(self, cmd_, data=None):
        ln = self.send(cmd_, data)
        return self.read(ln)

    ### common commands
    
    def reset(self):
        self.stream.read()
        self.send_read(BM_RESET)

    def start_ap(self):
        self.send_read(BM_START_SIMPLICITI)
        for i in xrange(10):
            res = self.send_read(BM_GET_SIMPLICITIDATA, [0x00, 0x00, 0x00, 0x00])
            res = self.send_read(BM_GET_STATUS, [0x00])

    def stop_ap(self):
        #The start access point command needs to come before the stop access point command
        #in order for the access point to turn off.
        self.send_read(BM_START_SIMPLICITI)
        self.send_read(BM_STOP_SIMPLICITI)

    def send_get_smpl_data(self):
        return self.send_read(BM_GET_SIMPLICITIDATA, [0x00, 0x00, 0x00, 0x00])

    def get_sync_buffer_status(self):
        res = self.send_read(BM_SYNC_GET_BUFFER_STATUS, [0x00])
        if self.debug >= 2:
            print "sync status", self.dstr(res)
        return ord(res[3])

    def wait_sync_buffer(self, timeout=1000, must=True):
        for i in xrange(timeout/5):
            status = self.get_sync_buffer_status()
            if status == must:
                return True
            msleep(5)

    def send_smpl_data(self, data, wait=False, timeout=1000):
        if len(data) != BM_SYNC_DATA_LENGTH:
            data = data[:BM_SYNC_DATA_LENGTH] + [0x00 for x in range(BM_SYNC_DATA_LENGTH-len(data))]
        snd = self.send_read(BM_SYNC_SEND_COMMAND, data)
#        return snd
        if wait:
            for i in xrange(timeout/30):
                msleep(30)
                status = self.get_sync_buffer_status()
                if status:
                   return ""#self.read_sync_data()
            #buf = self.send_get_smpl_data()
            #if buf != '\xff\x06\x07\xff\x00\x00\x00':
            #    print "OH read", repr(buf)
#           #     return
            #elif buf[4] == SYNC_AP_CMD_NOOP and buf[5] == SYNC_DATA_SENT:
            #    print "JUHU"
            #    return True
            #else:
            #    self.send_read(BM_SYNC_SEND_COMMAND, data)
        
        #status = self.status()
        #print "status", repr(status)

    def read_sync_data(self, data=None, timeout=3000):
        if not data:
            data = []
        if len(data) != BM_SYNC_DATA_LENGTH:
            data = data[:BM_SYNC_DATA_LENGTH] + [0x00 for x in range(BM_SYNC_DATA_LENGTH-len(data))]
        self.send(BM_SYNC_READ_BUFFER)
        red = self.read(BM_SYNC_DATA_LENGTH+3)
        print "read sync", self.dstr(red)
        return red

    def status(self):
        return self.send_read(BM_GET_STATUS, [0x00])

    @staticmethod
    def get_smpl_data(data, add=1):
        return data[SIMPLICITI_DATA_OFFSET+add:]


class CommandDispatcher(Simpliciti):

    debug = False

    HANDLERS = {
           BM_GET_STATUS:         "get_status",
           BM_SIMPLICITI_DATA:    "handle_smpl_data"
    }


    def cmd(self, cmd_, data):
        ln = self.send(cmd_, data)
        res = self.read()
        assert ln > 2
        if len(res) != ln:
            print "len differs", len(res), ln, repr(res)
            self.sync()
            return
        handler = getattr(self, self.HANDLERS.get(ord(res[1]), "default"))
        handler(res)

    def default(self, data):
        print "default"
        if self.debug:
            print "unhandled", self.dstr(data)

    def get_status(self, data):
        if self.debug:
            print res

    def handle_smpl_data(self, data):
        if self.debug > 2:
            print "got", repr(data)
        if len(data) < 4:
            return
        if ord(data[3]) == SIMPLICITI_NO_DATA:
            if self.debug > 3:
                print "got no data"
        else:
            if self.debug >= 1:
                print "handle", self.dstr(data)
            if hasattr(self, "smpl_%s" %"0x%0.2X" %ord(data[3])):
                getattr(self, "smpl_%s" %"0x%0.2X" %ord(data[3]))(data)
            else:
                self.smpl_default(data)

    def loop_smpl_get(self):
        while True:
            self.cmd(BM_GET_SIMPLICITIDATA, [0x00, 0x00, 0x00, 0x00])

    def smpl_default(self, data):
        print "default"
        if self.debug:
            print "unhandled", " ".join(["0x%0.2X" %ord(a) for a in self.get_smpl_data(data, 0)])

    """
    kinda messy

    Here's how this works.
    A packet for the watch sync looks like this:
    FF 31 16 03 94 34 01 07 DA 01 17 06 1E 00 00 00 00 00 00 00 00 00
    You have the first four bytes which we're just going to ignore.
    The 5th byte represents the hour you want to sync to.
    The 6th byte represents the minute you want to sync to.
    The 7th byte represents the second you want to sync to.
    The 9th byte represents the year you want to sync to.
    The 10th byte represents the month you want to sync to.
    The 11th byte represents the day you want to sync to.
    THe 14th and 15th bytes represent the temperature in celcius.
    The 16th and 17th bytes represent the altitude in meters.

    It also stores some of these values in some unusual (to me) ways.

    For hour, the value 0x80 needs to be added to the 24hr representation of the desired
    hour to sync to.

    For year the value 0x700 needs to be subtracted from the desired year to sync to.

    For temperature, the temperature (in celcius) needs to be multiplied by 0x0A.

    Caveat emptor: There is no error checking implemented to check for valid ranges.
    """
    #{'alarm_hour': 6, 'hour': 4, 'tempCelcius': 272, 'metric': 1, 'month': 8, 'second': 56, 'year': 2009, 'alarm_minute': 30, 'altMeters': 485, 'day': 1, 'minute': 50}
    def build_sync_data(self, kwargs):
        adjHour = kwargs['metric'] << 7 | kwargs['hour']
        adjYear = struct.pack('>H', kwargs['year'])
        adjTempCelcius = kwargs['temp_celcius'] # * 0x0A
        cmd = [SYNC_AP_CMD_SET_WATCH,
               adjHour,
               kwargs['minute'],
               kwargs['second'],
               ord(adjYear[0]),ord(adjYear[1]),
               kwargs['month'],
               kwargs['day'],
               kwargs['alarm_hour'],
               kwargs['alarm_minute']]

        hexCelcius = hex(adjTempCelcius)[2:].zfill(4)
        hexMeters = hex(kwargs['alt_meters'])[2:].zfill(4)

        for i in splitIntoNPieces(hexCelcius,2):
            cmd.append(int(i,16))
        for i in splitIntoNPieces(hexMeters,2):
            cmd.append(int(i,16))
    
        for i in xrange(0,3):
            cmd.append(0)
   
        return cmd

    def parse_sync_data(self, data, offset=3):
        if len(data) >= offset+13 and ord(data[offset]) == 0x03:
            # status data
            rv = {}
            # FIXME: fix am/pm code in hours
            rv["metric"] = ord(data[offset+1]) >> 7
            rv["hour"] = ord(data[offset+1])&0x7F
            rv["minute"] = ord(data[offset+2])
            rv["second"] = ord(data[offset+3])
            rv["year"] = struct.unpack('>H', array.array('B', [ord(data[offset+4]),ord(data[offset+5])]).tostring())[0]
            rv["month"] = ord(data[offset+6])
            rv["day"] = ord(data[offset+7])
            rv["alarm_hour"] = ord(data[offset+8])
            rv["alarm_minute"] = ord(data[offset+9])
            rv["temp_celcius"] = struct.unpack('>H', array.array('B', [ord(data[offset+10]),ord(data[offset+11])]).tostring())[0]
            rv["alt_meters"] = struct.unpack('>H', array.array('B', [ord(data[offset+12]),ord(data[offset+13])]).tostring())[0]
            return rv

class ProtocolView(CommandDispatcher):

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
        count = ord(mdata[2])
        print "%3d %6d %s" %(count, var, "#"*max(min((var/500), 80),1))


