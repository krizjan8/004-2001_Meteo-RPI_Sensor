"""
Raspberry Pi BME280 Driver.
"""
__version__ = "0.2.0"

import sys
import sqlalchemy as db
import configparser
import signal
import logging
import threading
from time import sleep
from debug import dummy_data
import datetime

class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully) #ctrl+c
        signal.signal(signal.SIGTERM, self.exit_gracefully) #systemd stop

    def exit_gracefully(self,signum, frame):
        self.kill_now = True

def opendb(db_config):

    tablename = db_config["tablename"]
    host = db_config["host"]
    user = db_config["user"]
    passwd = db_config["passwd"]
    database = db_config["db"]

    sqlserver = 'mysql://{0}:{1}@{2}/{3}'.format(user,passwd,host,database)
    engine = db.create_engine(sqlserver)
    meta = db.MetaData()  # co jsou metadata?
    table = db.Table(tablename, meta, autoload=True, autoload_with=engine)

    return {"table":table, "engine":engine}

#lists all sensors from config
def sens_from_cfg(config):
    sensors = list()
    i = 0

    while True:
        sensor = 'sensor{0}'.format(i)
        if not config.has_section(sensor):
            return sensors
        sensors.append(config[sensor])
        i = i + 1

class Sensor:

    sensors_ctn = 0 #number of sensors

    def __init__(self, sens_cfg, device, mode, database):
        self.running = False
        self.type = sens_cfg["type"]
        self.sampletime = float(sens_cfg["sampletime"])

        dev_id = device["id"]
        location = device["location"]
        table = database["table"]
        self.insert = table.insert().values(dev_id=dev_id, location=location)
        self.engine = database["engine"]
        self.inserts = list()

        Sensor.sensors_ctn = Sensor.sensors_ctn + 1 # increase number of sensors

    def sample_save_db(self):

        for type, value in self.sample().items(): #sample returns dict
            self.inserts.append(self.insert.values(value=value, value_type=type))

        conn = self.engine.connect()  # init

        for i in self.inserts:
            conn.execute(i)

        self.inserts.clear() #clear list

    def sample_print(self):
        print(self.type, ":".join([' {} {:.2f}'.format(k, v) for k, v in self.sample().items()]))

    #@abstractmethod todo
    def sample(self):
        pass

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        print("Sensor ", self.type, " is running.")  # todo logging
        while self.running:
            self.sample_save_db()
            sleep(self.sampletime)
        print("Sensor closed") #todo logging

class BMx280i2c(Sensor):

    def __init__(self, sens_cfg, device, mode, database):
        super().__init__(sens_cfg, device, mode, database)

        # i2c
        self.address = int(sens_cfg["address"],16)

        # common measurements
        self.temperature_tag = sens_cfg["temperature"]
        self.pressure_tag = sens_cfg["pressure"]

        # mode
        self.no_sensor = mode.getboolean("no_sensors")

        print(mode)
        if self.no_sensor is False:
            self.bus = smbus2.SMBus(int(sens_cfg["i2cport"]))
            bme280.load_calibration_params(self.bus, self.address)
    #@abstractmethod Todo
    def sample(self):
        pass

    def get_data(self):
        if self.no_sensor is False:
            return bme280.sample(self.bus, self.address)

        else:
            return dummy_data()

class BMP280i2c(BMx280i2c):

    def __init__(self, sens_cfg, device, mode, database):
        super().__init__(sens_cfg, device, mode, database)
        print("Starting BMP") # todo :  logging init ok.

    def sample(self):

        data = self.get_data()

        return {self.temperature_tag : data.temperature,
                self.pressure_tag : data.pressure}

class BME280i2c(BMx280i2c):

    def __init__(self, sens_cfg, device, mode, database):
        super().__init__(sens_cfg, device, mode, database)
        self.humidity_tag = sens_cfg["humidity"]
        print("Starting BME") # todo logging init ok.

    def sample(self):

        data = self.get_data()

        return {self.temperature_tag : data.temperature,
                self.pressure_tag : data.pressure,
                self.humidity_tag : data.humidity}

def init_sensor(type):
    switcher = {
        'BME280i2c': BME280i2c,
        'BMP280i2c': BMP280i2c
    }
    return switcher.get(type, None)

def close_app(senors):
    for s in sensors:
        s.stop()

#init sensor
if __name__ == '__main__': # Executed when invoked directly

    if 'win32' not in sys.platform:
        import bme280
        import smbus2

  # init
    config = configparser.ConfigParser()
    config.read("meteo_config.ini")

    device = config["device"]
    mode = config["mode"]
    threads = list()
    sensors = list()
    database = opendb(config["sqlsrv"])

    verbose_mode = True

    killer = GracefulKiller()

    for sens_cfg in sens_from_cfg(config):
        # init sensor depending on its type, returns sensor insance
        sensor = init_sensor(sens_cfg["type"])(sens_cfg, device, mode,
                             database)

        if sensor is not None:  # init_sensor returns None if sensor type not found (what if error during?)
            sensors.append(sensor)
            threads.append(threading.Thread(target=sensor.run, args=()))
        else:
            print("Configuration for sensor: ", sens_cfg["type"], " was not found!")

    # todo implement argparser
    if "-srv" in sys.argv:
        verbose_mode = False
        for t in threads:
            t.start()

    while not killer.kill_now:
        if verbose_mode is True:
            print(datetime.datetime.now())
            for sensor in sensors:
                sensor.sample_print()
            print()
            sleep(5)
        else:
            while True:
                pass

    print("App is closing") #todo logging
    close_app(sensors)

