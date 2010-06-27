import serial
import array
import sys
import struct

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
    #def 

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
        self.stream.write(res.tostring())
        return ln

    def sync(self):
        self.last_cmd = ()
        self.send_read(BM_GET_STATUS, [0x00])

    def read(self, ln=None):
        offset = 0
        self.rbuffer += self.stream.read(ln or self.last_cmd[1])
        
        if len(self.rbuffer) < 2:
            raise ValueError, "Not enough bytes returned"
        if ord(self.rbuffer[0]) != 0xFF:
            if not self.autosync:
                raise Warning, "Desync detected"
            for i in xrange(len(self.rbuffer)):
                if ord(self.rbuffer[i]) == 0xFF:
                    if ord(self.rbuffer[i+1]) == self.last_cmd[0] and \
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
        self.send_read(BM_RESET)

    def start_ap(self):
        self.send_read(BM_START_SIMPLICITI)

    def send_get_smpl_data(self):
        return self.send_read(BM_GET_SIMPLICITIDATA, [0x00, 0x00, 0x00, 0x00])

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
            print "unhandled", repr(data)

    def get_status(self, data):
        if self.debug:
            print res

    def handle_smpl_data(self, data):
        #print "handle", repr(data)
        if self.debug > 2:
            print "got", repr(data)
        if len(data) < 4:
            return
        if ord(data[3]) == SIMPLICITI_NO_DATA:
            if self.debug > 3:
                print "got no data"
        else:
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


