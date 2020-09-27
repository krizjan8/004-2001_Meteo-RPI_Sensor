import adafruit_max31865
import board
import busio
import digitalio
import time
import bme280
import smbus2
import datetime
import statistics as st
import signal

class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully) #ctrl+c
        signal.signal(signal.SIGTERM, self.exit_gracefully) #systemd stop

    def exit_gracefully(self,signum, frame):
        self.kill_now = True


spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D5)  # Chip select of the MAX31865 board.

rtd = adafruit_max31865.MAX31865(spi, cs, wires=4, rtd_nominal=100.0, ref_resistor=430.0)

port = 1
address_p = 0x76  # purple sensor# Adafruit BME280 address. Other BME280s may be different
address_r = 0x77  # red sensor
bus = smbus2.SMBus(port)

bme280.load_calibration_params(bus, address_p)
bme280.load_calibration_params(bus, address_r)

d = datetime.datetime.now()
f = open("calib_{:%Y%m%d-%H%M%S}.txt".format(d), "a")
f.write("time,temp_rtd [°C],temp_r [°C],temp_p [°C],humi_r [%],pressure_r [hPa],pressure_p [hPa]\n")

temp_rtd = []
temp_r = []
temp_p = []

killer = GracefulKiller()

while not killer.kill_now:
    tic = time.perf_counter()
    for i in range(0, 10):
        temp_rtd.append(rtd.temperature)
        r = bme280.sample(bus, address_r)
        p = bme280.sample(bus, address_p)
        temp_r.append(r.temperature)
        temp_p.append(p.temperature)
        humi_r = r.humidity
        press_r = r.pressure
        press_p = p.pressure

    d = datetime.datetime.now()
    string = '{:%Y-%m-%d %H:%M:%S},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f},{:.4f}\n'.format(d, st.mean(temp_rtd), st.mean(temp_r), st.mean(temp_p),
                                                            humi_r, press_r, press_p)
    print(string)
    f.write(string)
    while (time.perf_counter() - tic) <= 5:
        pass

f.close()
print('Finished succesfully!')
