from data.db_session import db_auth
import pymongo
import re

# Neo4j
graph = db_auth()

# mongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["SpaceLink"]
schedule_db = db['schedule']

ALLOWED_EXTENSIONS = {'csv', 'tsv'}
FILTER = ['lFilter','rFilter','gFilter','bFilter','haFilter','oiiiFilter','siiFilter','duoFilter','multispectraFilter', \
            'JohnsonU','JohnsonB','JohnsonV','JohnsonR','JohnsonI',\
            'SDSSu','SDSSg','SDSSr','SDSSi','SDSSz']
PATTERN = re.compile('.*[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9]')

# convert hms / dms to degree
def hms2degree(ra_hms: list, dec_dms: list):
    len_ra = len(ra_hms)
    len_dec = len(dec_dms)
    if len_ra != 0:
        ra_symbol = -1 if float(ra_hms[0]) < 0 else 1
    if len_dec != 0:
        dec_symbol = -1 if float(dec_dms[0]) < 0 else 1

    # transfer the unit of ra/dec from hms/dms to degrees
    if len_ra == 1:
        ra_degree = float(ra_hms[0]) * 15
    elif len_ra == 2:
        ra_degree = (float(ra_hms[0]) + ra_symbol*float(ra_hms[1])/60) * 15
    else:
        ra_degree = (float(ra_hms[0]) + ra_symbol*float(ra_hms[1])/60 + ra_symbol*float(ra_hms[2])/3600) * 15

    if len_dec == 1:
        dec_degree = float(dec_dms[0])
    elif len_dec == 2:
        dec_degree = float(dec_dms[0]) + dec_symbol*float(dec_dms[1])/60
    else:
        dec_degree = float(dec_dms[0]) + dec_symbol*float(dec_dms[1])/60 + dec_symbol*float(dec_dms[2])/3600

    return ra_degree, dec_degree

# convet degree to hms / dms
def degree2hms(ra='', dec='', _round=False):
    RA, DEC, rs, ds = '', '', '', ''
    if dec:
        if str(dec)[0] == '-':
            ds, dec = '-', abs(dec)
        degree = int(dec)
        decM = abs(int((dec-degree) * 60))
        if _round:
            decS = round((abs((dec-degree) * 60)-decM) * 60, 2)
        else:
            decS = (abs((dec-degree)*60)-decM) * 60
        DEC = '{0}{1} {2} {3}'.format(ds, degree, decM, decS)

    if ra:
        if str(ra)[0] == '-':
            rs, ra = '-', abs(ra)
        raH = int(ra/15)
        raM = int(((ra/15)-raH) * 60)
        if _round:
            raS = round(((((ra/15)-raH) * 60)-raM) * 60, 2)
        else:
            raS = ((((ra/15)-raH) * 60)-raM) * 60
        RA = '{0}{1} {2} {3}'.format(rs, raH, raM, raS)

    if ra and dec:
        return (RA, DEC)
    else:
        return RA or DEC

# Y get user's UID
def get_uid(usr: str):
    query_uid = "MATCH (x:user{email:$usr}) return x.UID as UID"
    uid = graph.run(query_uid, usr=usr).data()
    uid = int(uid[0]['UID'])

    return uid

# Y get the equipment id
def get_eid(uhaveid):
    query_eid = "MATCH (x:user)-[h:UhaveE{uhaveid:$uhaveid}]->(e:equipments) return e.EID as EID"
    eid = graph.run(query_eid, uhaveid=uhaveid).data()
    eid = int(eid[0]['EID'])

    return eid