import bme280
import smbus2
from time import sleep
import sqlalchemy as db


#constants
TABLENAME = 'records_test'
port = 1
address = 0x76 # Adafruit BME280 address. Other BME280s may be different
bus = smbus2.SMBus(port)

bme280.load_calibration_params(bus,address)
engine = db.create_engine('mysql://username:password@sql280.hosting/table')
meta = db.MetaData()
table = db.Table(TABLENAME, meta, autoload=True,autoload_with=engine)

while True:
    bme280_data = bme280.sample(bus,address)
    insTemp = table.insert()
    insTemp = insTemp.values(dev_id='RPI_0', location='Living Room')
    insTemp = insTemp.values(value = bme280_data.temperature, value_type = 'in_temp')

    insPress = table.insert()
    insPress = insPress.values(dev_id='RPI_0', location='Living Room')
    insPress = insPress.values(value = bme280_data.pressure, value_type='in_press')

    humidity = bme280_data.humidity
    insHumi = table.insert()
    insHumi = insHumi.values(dev_id='RPI_0', location='Living Room')
    insHumi = insHumi.values(value=bme280_data.humidity, value_type='in_humi')

    conn = engine.connect()
    conn.execute(insTemp)  # vlozeni
    conn.execute(insPress)
    if humidity != 0.0:
        conn.execute(insHumi)

    sleep(10)
