from services.classes import Target
from data.db_session import db_auth
from astroquery.simbad import Simbad
from services.project_service import update_project_equipment_observe_list
import webbrowser, json
from werkzeug.utils import secure_filename
import csv 
import re

FILTER = ['Johnson_B','Johnson_V','Johnson_R','SDSS_u','SDSS_g','SDSS_r','SDSS_i','SDSS_z']
PATTERN = re.compile('.*[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9]')

graph = db_auth()


#return all the target in the DB, this version limit the number to 100 
def get_target():
    # this function will return all target
    query = "MATCH(t:target) return t.name as name order by t.TID limit 100"
    # "MATCH(t:target) where t.tid>100 return t.name as name order by t.TID limit 100"
    target = graph.run(query)
    return target

#get a target's information
def get_targetDetails(targetName: str):
    query = "MATCH(t:target{name:$name}) return t.longitude as ra, t.latitude as dec, t.TID as TID"

    targetDetails = graph.run(query, name=targetName).data()
    return targetDetails

#get a target's node
def get_targetNode(targetName: str):
    query = "MATCH(t:target{name:$name}) return t"

    targetNode = graph.run(query, name=targetName).data()
    return targetNode

#search a target by keyword
def search_target(text: str):
    query= "MATCH (t:target) where t.name =~ $text return t.name as name order by t.name "
    target = graph.run(query, text = text).data()
    print(target)
    return target

# add target in Simbad to target table
def query_from_simbad(targetName: str):
    limitedSimbad = Simbad()
    limitedSimbad.ROW_LIMIT = 5

    result_table = limitedSimbad.query_object(targetName)

    if result_table:
        ra = result_table[0][1]
        dec = result_table[0][2]

        ra_split = ra.split(" ")
        dec_split = dec.split(" ")

        len_ra = len(ra_split)
        len_dec = len(dec_split)

        # transfer the unit of ra/dec from hms/dms to degrees
        if len_ra == 1:
            ra_degree = float(ra_split[0]) * 15
        elif len_ra == 2:
            ra_degree = (float(ra_split[0]) + float(ra_split[1])/60) * 15
        else:
            ra_degree = (float(ra_split[0]) + float(ra_split[1])/60 + float(ra_split[2])/3600) * 15

        if len_dec == 1:
           dec_degree = float(dec_split[0])
        elif len_dec == 2:
            dec_degree = float(dec_split[0]) + float(dec_split[1])/60
        else:
            dec_degree = float(dec_split[0]) + float(dec_split[1])/60 + float(dec_split[2])/3600
            
        webbrowser.open("https://simbad.u-strasbg.fr/simbad/sim-basic?Ident=" + targetName + "&submit=SIMBAD+search")

        # check if the target exist in target table
        if(not get_targetDetails(targetName)):
            # create the target
            count = graph.run("MATCH (t:target) return t.TID  order by t.TID DESC limit 1 ").data()
            
            target = Target()
            if len(count) == 0:
                target.TID = 0
            else:
                target.TID = count[0]['t.TID']+1
            target.name = targetName
            target.longitude = ra_degree
            target.latitude = dec_degree
            graph.create(target)            
            print("NAME", target.name)

            return [{'name': target.name}]
        else:
            print("Target is already in the target table")
            return [{'name': targetName}]
    else:
        print("Target doesn't exist.")

    
def allowed_file(filename: str):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_format(filename: str):
    #print(filename)
    with open(filename, newline="") as csvfile:
        rows = csv.DictReader(csvfile)

        for index, row in enumerate(rows):
            #name check
            if len(row['Name']) == 0:
                return "rows "+ str(index+1) + " error : Please enter target name" 
            elif len(row['Name']) > 50 :
                return "rows "+ str(index+1) + " error : Name is too long"

            #ra check
            try:
                ra = float(row['ra'])
                if  ra < 0 or ra > 360 :
                    return "rows "+ str(index+1) + " error : RA format error"
            except ValueError:
                try :
                    result = PATTERN.match(row['ra'])
                    #print(result)
                    if result == None: 
                        raise Exception
                    
                    #print(result.group())
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
            
            #dec check
            try:
                dec = float(row['dec'])
                if dec < -90 or dec > 90:
                    return "rows "+ str(index+1) + " error : Dec format error"
            except ValueError:
                try :
                    result = PATTERN.match(row['dec'])
                    if result == None: 
                        raise Exception
                    
                    #print(result.group())
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
            
            #filter and mode check
            mode = int(row['Mode'])
            if mode < 0 or mode > 2 :
                return "rows "+ str(index+1) + " error : Mode format error"      
            
            for filter in FILTER:
                if row[filter].lower() != 'y' and row[filter].lower() != "n" and row[filter].lower() != 'yes' and row[filter].lower() != 'no':
                    return "rows "+ str(index+1) + " error : " + filter + " format error"      
                if not mode and row[filter] == 'Y':
                    try:
                        time = float(row[filter+'_Time']) 
                        if time < 0 :
                            raise Exception
                    except ValueError: 
                        return "rows "+ str(index+1) + " error : \"" + filter + "_Time\" format error"   

            if mode:
                try:
                    time = float(row['Total_cycle__time'])
                    if time < 0:
                        raise Exception
                except ValueError:
                    return "rows "+ str(index+1) + " error : \"Total cycle time\" format error"   

    csvfile.close()
    return "Success"

def upload_2_DB(filename : str, PID : int, usr: str):
    
    with open(filename, newline="") as csvfile:
        rows = csv.DictReader(csvfile)
        
        for index,row in rows:
            #change coordinate unit to degree
            try:
                float(row['ra'])
            except Exception:
                h,m,s= row['ra'].split(':',3)    
                h = float(h)
                m = float(m)
                s = float(s)
                row['ra'] = (h+ m/60+ s/3600) * 15
        
            #change coordinate unit to degree
            try:
                float(row['dec'])
            except Exception:
                d,m,s= row['dec'].split(':',3)    
                d = float(d)
                m = float(m)
                s = float(s)
                row['dec'] = h+ m/60+ s/3600

            print(row['ra'],row['dec'])
            #query by coordinate to check target exist or not
            query = "MATCH(t:target{ra:$ra, dec:$dec}) return t.TID as TID"
            result = graph.run(query,ra = row['ra'],dec=row['dec']).data()
            if not len(result):
                #if not, create the target node 
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


            for filter in FILTER:
                if row[filter].lower() == 'y' or row[filter].lower() == 'yes':
                    row[filter] = 'y'
                elif row[filter].lower() == 'n' or row[filter].lower() == 'no':
                    row[filter] = 'n'
                time2observe.append(float(row[filter+'_+Time']))

            #create project target relationship
            query="MATCH (p:project {PID: $PID}) MATCH (t:target {TID:$TID}) create (p)-[pht:PHaveT {phavetid:$phavetid, JohnsonB:$JohnsonB, JohnsonV:$JohnsonV, JohnsonR:$JohnsonR, SDSSu:$SDSSu, SDSSg:$SDSSg, SDSSr:$SDSSr, SDSSi:$SDSSi, SDSSz:$SDSSz, Time_to_Observe:$time2observe, Mode:$mode }]->(t) return pht.phavetid"
            update_project_equipment_observe_list(usr,PID,TID,row['Johnson_B'], row['Johnson_R'], row['Johnson_V'],row['SDSS_u'],row['SDSS_g'],row['SDSS_r'],row['SDSS_i'],row['SDSS_z'])
            count = graph.run("MATCH ()-[pht:PHaveT]->() return pht.phavetid  order by pht.phavetid DESC limit 1 ").data()
            if len(count) == 0:
                cnt = 0
            else:
                cnt = count[0]['pht.phavetid']+1
                result = graph.run(query, PID = PID, TID = TID, phavetid = cnt, JohnsonB = row['Johnson_B'], JohnsonR = row['Johnson_R'], JohnsonV = row['Johnson_B'] \
                    , SDSSg = row['SDSS_g'], SDSSi = row['SDSS_i'], SDSSr = row['SDSS_r'], SDSSu = row['SDSS_u'], SDSSz = row['SDSS_z'], Time_to_Observe= time2observe, mode=row['Mode']).data()

    return 1
