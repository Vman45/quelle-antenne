import sqlite3
from flask import Flask
from flask_cors import CORS, cross_origin
import math
import logging


logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


@app.route('/')
@cross_origin()
def hello_world():
    return antennasToJson(fetchAntennas(0,0,0,0))

@app.route('/supports/<float:centerLat>/<float:centerLon>/<float:distance>', methods=['GET'])
@cross_origin()
def getSupport(centerLat, centerLon, distance):
    upperLeftLat, upperLeftLon = destination(centerLat, centerLon, distance, 315)
    bottomRightLat, bottomRigthLon = destination(centerLat, centerLon, distance, 135)
    app.logger.debug('Bounding box ('+str(upperLeftLat)+', '+str(upperLeftLon)+') ('+str(bottomRightLat)+', '+str(bottomRigthLon)+')')
    return antennasToJson(fetchAntennas(upperLeftLat, upperLeftLon, bottomRightLat, bottomRigthLon))
    

def fetchAntennas(upperLeftLat, upperLeftLon, bottomRightLat, bottomRigthLon):
    
    conn = sqlite3.connect('quelle-antenne.sqlite3')
    c = conn.cursor()

    """ Get only 4G """
    """ Remove parabolic antennas which correspond to the link between relay """

    c.execute('select distinct sup.sup_id, lat, lon, ant.AER_ID, AER_NB_ALT_BAS, AER_NB_AZIMUT, ex.adm_lb_nom '
    'from SUP_SUPPORT sup '
    'inner join SUP_STATION sta '
    'on sta.sta_nm_anfr = sup.sta_nm_anfr '
    'inner join SUP_EXPLOITANT ex '
    'on ex.ADM_ID = sta.ADM_ID '
    'inner join SUP_ANTENNE ant '
    'on ant.sta_nm_anfr = sup.sta_nm_anfr '
    'inner join SUP_EMETTEUR em '
    'on em.sta_nm_anfr = sup.sta_nm_anfr '
    'inner join SUP_TYPE_ANTENNE t '
	'on t.TAE_ID = ant.TAE_ID '
    'where sup.lat < ? and sup.lat > ? and sup.lon > ? and sup.lon < ? '
    'and ex.ADM_ID in (6, 137, 23, 240)  '
    'and em.emr_lb_systeme like "LTE%" ' 
    'and t.TAE_ID <> 17 ' 
    'and AER_NB_ALT_BAS >= 0 '
    'order by sup.sup_id, AER_NB_ALT_BAS, ant.AER_ID;', (upperLeftLat, bottomRightLat, upperLeftLon, bottomRigthLon,))


    rows = c.fetchall()
    conn.close()

    return rows

def antennasToJson(rows):
    data = {"supports": []}

    currentSupId = 0
    currentHaut = 0
    currentAerId = 0
    currentSupport = None
    currentAntennaHeight = None
    currentAntenna = None

    for row in rows:
        print(row)
        app.logger.debug(row)
        supID = int(row[0])
        lat = float(row[1])
        lon = float(row[2])
        aerID = int(row[3])
        haut = float(row[4].replace(",", "."))
        # If the value corresponding to azimut is not set the antenna is
        # omnidirectionnal. A negative azimut represents that type of antenna.
        azimut = -1
        if(not (row[5] == '') ):
            azimut = float(row[5].replace(",", "."))
        operator = row[6]


        if(supID != currentSupId):
            currentSupport = {"supId" : supID, "lat": lat, "lon": lon, "antennes": []}
            data["supports"].append(currentSupport)

            currentAntennaHeight = {"haut": haut, "aer_ids": [], "isVisible": 1}
            currentSupport["antennes"].append(currentAntennaHeight)

            currentAntenna = {"aer_id" : aerID, "azimut": azimut, "operators" : []}
            currentAntennaHeight["aer_ids"].append(currentAntenna)

            currentSupId = supID
            currentHaut = haut
            currentAerId = aerID

        if(haut != currentHaut):
            currentAntennaHeight = {"haut": haut, "aer_ids": [], "isVisible": 1}
            currentSupport["antennes"].append(currentAntennaHeight)
            currentHaut = haut

        if(aerID != currentAerId):
            currentAntenna = {"aer_id" : aerID, "azimut": azimut, "operators": []}
            currentAntennaHeight["aer_ids"].append(currentAntenna)
            currentAerId = aerID

        currentAntenna["operators"].append(operator)

    return data

def destination(lat, lon, distance, bearing):
    """ Compute the point located at the distance and bearing from the given {lat, lon} origin point.
        Inspired by https://gist.github.com/marcus-at-localhost/39a346e7d7f872187124af9cd582f833

    Parameters
    ----------
    distance : float
        Distance in km.
    bearing : float
        Angle in degrees from geographic north.
    
    Returns
    -------
    json
        lat and lon of the destination point.
    """
    earthRadius = 6378.1 # Equatorial radius for unity in kilometers

    latRad = math.radians(lat)
    lonRad = math.radians(lon)
    bearingRad = math.radians(bearing)

    # New latitude in radians.
    new_latitude = math.asin(math.sin(latRad) * math.cos(distance / earthRadius) + math.cos(latRad) * math.sin(distance / earthRadius) * math.cos(bearingRad))

    # New longitude in radians.
    new_longitude = lonRad + math.atan2(math.sin(bearingRad) * math.sin(distance / earthRadius) * math.cos(latRad), math.cos(distance / earthRadius) - math.sin(latRad) * math.sin(new_latitude))

    return [math.degrees(new_latitude), math.degrees(new_longitude)]


if __name__ == '__main__':
    app.run(debug=True)