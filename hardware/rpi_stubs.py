# provide RPI stubs to allow for compilation on Windows

class gpio_stubs:
    OUT = 1
    IN = 1

    NO_EDGE =       0
    RISING =   1
    FALLING =  2
    BOTH =     3

    PUD_OFF  = 0
    PUD_DOWN = 1
    PUD_UP = 2

    INPUT  = 1
    OUTPUT = 0

    HIGH  = 1
    LOW = 0

    MODE_UNKNOWN = -1
    BOARD  = 10
    BCM = 11
    SERIAL = 40
    SPI = 41
    I2C = 42
    PWM = 43

    def log(msg):
        print("GPIO => {0}".format(msg))

    def setmode(a):
       gpio_stubs.log("setmode: {0}".format(a))

    def setup(channel,direction, pull_up_down,initial=None):
        gpio_stubs.log("setup: {0} - {1}".format(channel,direction))

    def output(channel, value):
        gpio_stubs.log("output: {0} - {1}".format(channel,value))

    def cleanup():
        gpio_stubs.log("cleanup")

    def setwarnings(flag):
        gpio_stubs.log("setwarnings: {0}".format(flag))

    def add_event_detect(channel, edge, callback, bouncetime=None):
        gpio_stubs.log("add_event_detect: pin({0})  edges={1}".format(channel,edge) )
    
    def remove_event_detect(channel):
        gpio_stubs.log("remove_event_detect: pin({0})".format(channel) )

    def input(channel):
        gpio_stubs.log("input: pin({0})".format(channel))