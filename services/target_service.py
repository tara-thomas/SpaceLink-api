from services.classes import Target
from data.db_session import db_auth
from astroquery.simbad import Simbad
import astropy.coordinates as coord
import astropy.units as u
from services.project_service import update_project_equipment_observe_list, create_project_target
from services.utils import *
import webbrowser, json
from werkzeug.utils import secure_filename
import csv 
import re

FILTER = ['lFilter','rFilter','gFilter','bFilter','haFilter','oiiiFilter','siiFilter','duoFilter','multispectraFilter', \
            'JohnsonU','JohnsonB','JohnsonV','JohnsonR','JohnsonI',\
            'SDSSu','SDSSg','SDSSr','SDSSi','SDSSz']
PATTERN = re.compile('.*[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9]')

graph = db_auth()


# return all the target in the DB, this version limit the number to 100 
def get_target():
    # this function will return all target
    query = "MATCH(t:target) return t.name as name order by t.TID limit 100"
    # "MATCH(t:target) where t.tid>100 return t.name as name order by t.TID limit 100"
    target = graph.run(query)
    return target

# get a target's information
def get_targetDetails(targetName: str):
    query = "MATCH(t:target{name:$name}) return t.longitude as ra, t.latitude as dec, t.TID as TID"

    targetDetails = graph.run(query, name=targetName).data()
    return targetDetails

# get a target's node
def get_targetNode(targetName: str):
    query = "MATCH(t:target{name:$name}) return t"

    targetNode = graph.run(query, name=targetName).data()
    return targetNode

# search a target by keyword
def search_target(text: str):
    query= "MATCH (t:target) where t.name =~ $text return t.name as name order by t.name "
    target = graph.run(query, text = text).data()
    print(target)
    return target

# 1020 create target if it doesn't exist
def create_target(targetName: str, ra: float, dec: float):
    targetDetail = get_targetDetails(targetName)
    if not targetDetail:
        # create the target
        count = graph.run("MATCH (t:target) return t.TID  order by t.TID DESC limit 1 ").data()
        
        target = Target()
        if len(count) == 0:
            target.TID = 0
        else:
            target.TID = count[0]['t.TID']+1
        target.name = targetName
        target.longitude = ra
        target.latitude = dec
        graph.create(target)            

        return "New target created!", target.TID
    else:
        return "Target already exists.", targetDetail[0]['TID']

# add target in Simbad to target table (1020 modify)
def query_simbad_byName(targetName: str):
    limitedSimbad = Simbad()
    limitedSimbad.ROW_LIMIT = 5

    result_table = limitedSimbad.query_object(targetName)

    if result_table:
        ra = result_table[0][1]
        dec = result_table[0][2]

        ra_split = ra.split(" ")
        dec_split = dec.split(" ")

        ra_degree, dec_degree = hms2degree(ra_split, dec_split)
            
        # webbrowser.open("https://simbad.u-strasbg.fr/simbad/sim-basic?Ident=" + targetName + "&submit=SIMBAD+search")
        simbad_link = "https://simbad.u-strasbg.fr/simbad/sim-basic?Ident=" + targetName + "&submit=SIMBAD+search"

        return {'name': targetName, 'ra': ra_degree, 'dec': dec_degree, 'link': simbad_link}
    else:
        print("Target doesn't exist.")
        return None

# 1020
def query_simbad_byCoord(targetCoord: str, rad: float, unit: str):
    limitedSimbad = Simbad()
    limitedSimbad.ROW_LIMIT = 5
    # setup unit
    if unit == "arcmin":
        unit = u.arcmin
    elif unit == "arcsec":
        unit = u.arcsec
    elif unit == "deg":
        unit = u.deg

    # ra and dec in degree
    if targetCoord.find(":") == -1:
        ra_degree, dec_degree = targetCoord.split(" ")
        ra_degree = float(ra_degree)
        dec_degree = float(dec_degree)
    # (h:m:s d:m:s) format
    else:
        ra_hms, dec_dms = targetCoord.split(" ")
        ra_degree, dec_degree = hms2degree(ra_hms.split(":"), dec_dms.split(":"))

    result_table = limitedSimbad.query_region(coord.SkyCoord(ra_degree, dec_degree,unit=(u.deg, u.deg), frame='icrs'), radius=rad * unit)
    tar_list = []
    for tar in result_table:
        ra, dec = hms2degree(tar[1].split(" "), tar[2].split(" "))
        tar_list.append({'name': tar[0], 'ra': ra, 'dec': dec})

    return tar_list
    
# def allowed_file(filename: str):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_format(filename: str):
    #print(filename)
    with open(filename, newline="") as csvfile:
        rows = csv.DictReader(csvfile)

        for index, row in enumerate(rows):
            # name check
            if len(row['Name']) == 0:
                return "rows "+ str(index+1) + " error : Please enter target name" 
            elif len(row['Name']) > 50 :
                return "rows "+ str(index+1) + " error : Name is too long"

            # ra check
            try:
                ra = float(row['ra'])
                if  ra < 0 or ra > 360 :
                    return "rows "+ str(index+1) + " error : RA format error"
            except ValueError:
                try :
                    result = PATTERN.match(row['ra'])
                    # print(result)
                    if result == None: 
                        raise Exception
                    
                    # print(result.group())
                    h,m,s= result.group().split(':',3)
                    
                    h = float(h)
                    m = float(m)
                    s = float(s)
                    if h < 0 or h > 23:
                        raise Exception
                    if m < 0 or m > 59:
                        raise Exception
                    if s < 0 or s > 59.9:
                        raise Exception
                    
                    ra = (h+ m/60+ s/3600) * 15

                except Exception:
                    return "rows "+ str(index+1) + " error : RA format error"
                pass
            
            # dec check
            try:
                dec = float(row['dec'])
                if dec < -90 or dec > 90:
                    return "rows "+ str(index+1) + " error : Dec format error"
            except ValueError:
                try :
                    result = PATTERN.match(row['dec'])
                    if result == None: 
                        raise Exception
                    
                    # print(result.group())
                    d,m,s= result.group().split(':',3)
                    
                    d = float(d)
                    m = float(m)
                    s = float(s)
                    print(d,m,s)
                    if d < -90 or d > 90:
                        raise Exception
                    if m < 0 or m > 59:
                        raise Exception
                    if s < 0 or s > 59.9:
                        raise Exception

                    dec = d + m/60 + s/3600
                except Exception:
                    return "rows "+ str(index+1) + " error : Dec format error"
                pass
            
            # filter and mode check
            mode = int(row['Mode'])
            if mode < 0 or mode > 2 :
                return "rows "+ str(index+1) + " error : Mode format error"      
            
            for filter in FILTER:
                if row[filter].isdigit() :
                    if int(row[filter]) < 0 :
                        return "rows "+ str(index+1) + " error : \"" + filter + " Time\" format error"   
                else:
                    return "rows "+ str(index+1) + " error : " + filter + " format error. "      


            # if mode:
            #     try:
            #         time = float(row['Total_cycle__time'])
            #         if time < 0:
            #             raise Exception
            #     except ValueError:
            #         return "rows "+ str(index+1) + " error : \"Total cycle time\" format error"   

    csvfile.close()
    return "Success"

def upload_2_DB(filename : str, PID : int, usr: str):
    
    with open(filename, newline="") as csvfile:
        rows = csv.DictReader(csvfile)
        
        for index,row in rows:
            # change coordinate unit to degree
            try:
                float(row['ra'])
            except Exception:
                h,m,s= row['ra'].split(':',3)    
                h = float(h)
                m = float(m)
                s = float(s)
                row['ra'] = (h+ m/60+ s/3600) * 15
        
            # change coordinate unit to degree
            try:
                float(row['dec'])
            except Exception:
                d,m,s= row['dec'].split(':',3)    
                d = float(d)
                m = float(m)
                s = float(s)
                row['dec'] = h+ m/60+ s/3600

            print(row['ra'],row['dec'])
            # query by coordinate to check target exist or not
            query = "MATCH(t:target{ra:$ra, dec:$dec}) return t.TID as TID"
            result = graph.run(query,ra = row['ra'],dec=row['dec']).data()
            if not len(result):
                # if not, create the target node 
                count = graph.run("MATCH (t:target) return t.TID  order by t.TID DESC limit 1 ").data()
                target = Target()
                if len(count) == 0:
                    target.TID = 0
                else:
                    target.TID = count[0]['t.TID']+1
                    TID = target.TID
                target.name = row['Name']
                target.longitude = row['ra']
                target.latitude = row['dec']
                graph.create(target) 
            else:
                TID = int(result['TID']) 
            
            
            time2observe = []
            filter2observe = []

            for filter in FILTER:
                if(int(row[filter]) > 0):
                    filter2observe.append(True)
                else:
                    filter2observe.append(False)
                time2observe.append(int(row[filter]))

            # create project target relationship
            create_project_target(usr, PID, TID, filter2observe, time2observe, int(row['Mode']))
            # query="MATCH (p:project {PID: $PID}) MATCH (t:target {TID:$TID}) create (p)-[pht:PHaveT {phavetid:$phavetid, JohnsonB:$JohnsonB, JohnsonV:$JohnsonV, JohnsonR:$JohnsonR, SDSSu:$SDSSu, SDSSg:$SDSSg, SDSSr:$SDSSr, SDSSi:$SDSSi, SDSSz:$SDSSz, Time_to_Observe:$time2observe, Mode:$mode }]->(t) return pht.phavetid"
            # update_project_equipment_observe_list(usr,PID,TID,row['Johnson_B'], row['Johnson_R'], row['Johnson_V'],row['SDSS_u'],row['SDSS_g'],row['SDSS_r'],row['SDSS_i'],row['SDSS_z'])
            # count = graph.run("MATCH ()-[pht:PHaveT]->() return pht.phavetid  order by pht.phavetid DESC limit 1 ").data()
            # if len(count) == 0:
            #     cnt = 0
            # else:
            #     cnt = count[0]['pht.phavetid']+1
            #     result = graph.run(query, PID = PID, TID = TID, phavetid = cnt, JohnsonB = row['Johnson_B'], JohnsonR = row['Johnson_R'], JohnsonV = row['Johnson_B'] \
            #         , SDSSg = row['SDSS_g'], SDSSi = row['SDSS_i'], SDSSr = row['SDSS_r'], SDSSu = row['SDSS_u'], SDSSz = row['SDSS_z'], Time_to_Observe= time2observe, mode=int(row['Mode'])).data()

    return 1


def time_deduction(PID: int, TID: int, observe_time: list):
    
    remain = get_remain_time_to_observe(PID,TID)
    for i in len(observe_time):
        remain[i] = remain[i] - observe_time[i]

    set_remain_time_to_observe(PID,TID)

    return 1

def set_remain_time_to_observe(PID: int, TID: int, remain: list):
    query = "match x=(p:project{PID:$pid})-[r:PHaveT]->(t:target{TID:$tid}) set r.Remain_to_Observe={ramain:$remain} return r.Remain_to_Observe as remain" #update new time_to_observe
    result = graph.run(query, pid = PID, tid = TID).data()
    print(result[0]['remain'])
    return

def get_remain_time_to_observe(PID: int, TID: int):
    
    query = "match x=(p:project{PID:$pid})-[r:PHaveT]->(t:target{TID:$tid}) return r.Remain_to_Observe as remain"  #query old time_to_observe
    time = graph.run(query, pid = PID, tid = TID).data()
    return time[0]['remain']

def get_time_to_observe(PID: int, TID: int):
    
    query = "match x=(p:project{PID:$pid})-[r:PHaveT]->(t:target{TID:$tid}) return r.Time_to_Observe as time"  #query origin time_to_observe
    time = graph.run(query, pid = PID, tid = TID).data()
    return time[0]['time']



