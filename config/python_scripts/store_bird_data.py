import mysql.connector
from homeassistant.const import STATE_UNKNOWN

def run_script(hass, data):
    bird_name = data.get('birdName')
    event_time = data.get('time')
    event_count = data.get('eventCount')
    confidence = data.get('confidence')

    if bird_name is None or event_time is None or event_count is None or confidence is None:
        logger.error("None of the required parameters is provided.")
        return

    try:
        db = mysql.connector.connect(
          host="192.168.3.7",  #replace with your MariaDB host
          user="admin",  #replace with your MariaDB username
          password="Zb0dcVJNdj",  #replace with your MariaDB password
          database="birddb"  #replace with your database name
        )
        cursor = db.cursor()

        sql_query = "INSERT INTO BirdNetData (time, birdName, eventCount, confidence) VALUES (%s, %s, %s, %s)"
        values = (event_time, bird_name, event_count, confidence)

        cursor.execute(sql_query, values)
        db.commit()

    except Exception as e:  
        logger.error("Problem accessing MariaDB: %s" % str(e))
        return

    logger.info("Data stored to MariaDB successfully.")
