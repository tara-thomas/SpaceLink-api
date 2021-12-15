from data.db_session import db_auth
from typing import Optional
from passlib.handlers.sha2_crypt import sha512_crypt as crypto
from services.classes import User, Target, Equipments, Project, Schedule
from datetime import datetime, timedelta
# from services.schedule_service import create_schedule

import astro.declination_limit_of_location as declination
import astro.astroplan_calculations as schedule
import astro.nighttime_calculations as night
import ephem
import random
import numpy as np

graph = db_auth()

# find the user node bt email
def find_user(email: str):
    user = User.match(graph, f"{email}")
    return user

# create a new user
def create_user(username: str, name: str, email: str, affiliation: str, title: str, country: str, password: str) -> Optional[User]:
    
    if find_user(email):  #Check user exist or not
        return None
    
    user = User()
    
    max_id = graph.run(f"MATCH (u:user) RETURN u.UID order by u.UID DESC LIMIT 1").data()  #generate a id for user
    print(max_id)
    if len(max_id) == 0:
        user.UID = 0
    else:
        user.UID = max_id[0]['u.UID']+1
    
    user.username = username
    user.name = name
    user.email = email
    user.affiliation = affiliation
    user.title = title
    user.country = country
    user.hashed_password = hash_text(password)
    
    graph.create(user)
    return user

# password encryption funcrion
def hash_text(text: str) -> str:
    hashed_text = crypto.encrypt(text, rounds=171204)
    return hashed_text

# password verify vunction
def verify_hash(hashed_text: str, plain_text: str) -> bool:
    return crypto.verify(plain_text, hashed_text)

#login function
def login_user(email: str, password: str) -> Optional[User]:
    
    user = User.match(graph, f"{email}").first()
    if not user:  #check user exist or not
        print(f"Invalid User - {email}")
        return None
    if not verify_hash(user.hashed_password, password): #check the password correct or not
        print(f"Invalid Password for {email}") 
        return None
    print(f"User {email} passed authentication")
    return user

# get user's profile
def get_profile(usr: str) -> Optional[User]:
    # user = User.match(graph, f"{usr}").first()
    user_profile = graph.run(f"MATCH (x:user) WHERE x.email='{usr}' RETURN x.username as username, x.name as name, x.email as email, x.affiliation as affiliation, x.title as title, x.country as country").data()
    return user_profile

# update user's profile
def update_profile(usr: str, username: str, name: str, affiliation: str, title: str, country: str) -> Optional[User]:
    # user = User.match(graph, f"{usr}").first()
    query = f"MATCH (x:user) WHERE x.email='{usr}' SET x.username='{username}', x.name='{name}', x.affiliation='{affiliation}', x.title='{title}', x.country='{country}'" \
    "RETURN x.username as username, x.name as name, x.email as email, x.affiliation as affiliation, x.title as title, x.country as country"
    user_profile = graph.run(query).data()
    return user_profile

# returns the number of user in the DB
def count_user():
    query = "match (x:user) return x.UID as max order by max DESC limit 1"
    count = graph.run(query).data()

    return int(count[0]['max'])

# get user's UID
def get_uid(usr: str):
    query_uid = "MATCH (x:user{email:$usr}) return x.UID as UID"
    uid = graph.run(query_uid, usr=usr).data()
    uid = int(uid[0]['UID'])

    return uid

# returns the number of equipment of a user
def count_user_equipment(usr: str)->int:
    count = graph.run("MATCH (x:user {email:$usr})-[:UhaveE]->(:equipments) return count(*)",usr=usr).evaluate()
    return count

# create a new equipment for user , this is a relationship called "UHaveE"
def create_user_equipments(usr: str, eid: int, site: str, longitude: float, latitude: float, altitude: float, tz: str, sq: float):
    query ="MATCH (x:user {email:$usr})  MATCH (e:equipments {EID:$EID})" \
    "CREATE (x)-[h:UhaveE{ uhaveid: $uhaveid, site:$Site, longitude:$Longitude, latitude:$Latitude" \
    ", altitude:$Altitude, time_zone:$tz, sky_quality:$sq, declination_limit:$declination_limit}]->(e) return h.uhaveid as id, h.site as site, h.longitude as longitude," \
    "h.latitude as latitude, h.altitude as altitude, h.time_zone as time_zone, h.sky_quality as sky_quality"

    count = graph.run("MATCH (x:user)-[p:UhaveE]->(:equipments) return p.uhaveid order by p.uhaveid DESC limit 1").data()
    if len(count) == 0:
        uhaveid = 0
    else:
        uhaveid = count[0]['p.uhaveid']+1
    print(uhaveid)
    user_equipments = graph.run(query,usr=usr, EID = eid, Site=site, Longitude=longitude, Latitude=latitude, Altitude=altitude, tz=tz, sq=sq, uhaveid = uhaveid, declination_limit=0)
    
    # calculate the declination limit of the equipment and update the table
    update_declination(uhaveid)

    # create a empty schedule for the equipment
    # _ = create_schedule(eid, uhaveid)

    return user_equipments

# update the equipment's information
# def update_user_equipments(aperture: float,Fov: float,pixel_scale: float,tracking_accuracy: float,lim_magnitude: float,elevation_lim: float,mount_type: str,camera_type1:str,
#                           camera_type2: str,JohnsonB: str,JohnsonR: str,JohnsonV: str,SDSSu: str,SDSSg: str,SDSSr: str,SDSSi: str,SDSSz:str,
#                           usr: str ,Site: str,Longitude:float,Latitude:float,Altitude:float,tz:str,daylight:bool,wv: float,light_pollution: float, uhaveid : int):
def update_user_equipments(telName: str, focalLength: float, diameter: float,
                        camName: str, pixelSize: float, sensorW: float, sensorH: float, camera_type1: str, camera_type2: str, filterArray: list,
                        mountName: str, mount_type: str, deg: float, barlowName: str, magnification: float,
                        usr: str, uhaveid: int, site: str, longitude: float, latitude: float, altitude: float, tz: str, sq: float):

    # calculated specs (need to save focalRatio, fovDeg, and resolution)
    focalRatio = focalLength * magnification / diameter
    sensorSize = pixelSize * sensorW / 1000
    fovRad = np.arctan(sensorSize / (focalLength * magnification))
    fovDeg = fovRad * 360 / (2 * np.pi)
    fovArcsec = fovDeg * 3600
    resolution = fovArcsec / sensorW

    query ="MATCH (x:user {email:$usr})-[h:UhaveE {uhaveid: $uhaveid}]->(e:equipments)" \
             f"SET h.site='{site}', h.longitude='{longitude}', h.latitude='{latitude}', h.altitude='{altitude}', h.time_zone='{tz}', h.sky_quality='{sq}'," \
             f"e.telName='{telName}', e.focalLength='{focalLength}', e.diameter='{diameter}',e.camName='{camName}', e.pixelSize='{pixelSize}', e.sensorW='{sensorW}', e.sensorH='{sensorH}', e.camera_type1='{camera_type1}', e.camera_type2='{camera_type2}',"\
             f"e.filterArray='{filterArray}', e.mountName='{mountName}', e.mount_type='{mount_type}', e.deg='{deg}', e.barlowName='{barlowName}', e.magnification='{magnification}', e.focalRatio='{focalRatio}', e.fovDeg='{fovDeg}', e.resolution='{resolution}'" 
    user_equipments = graph.run(query ,usr = usr, uhaveid = uhaveid)
    update_declination(uhaveid)
    return user_equipments

# return the information of a user's equipment
def get_user_equipments(usr: str):
    # return the user's equipment and that equipment's detail
    if  count_user_equipment(usr) == 0:
        return None
    user_equipments = graph.run("MATCH (x:user {email:$usr})-[h:UhaveE]->(e:equipments) return e.EID as eid,h.site as site, h.longitude as longitude," \
        "h.latitude as latitude, h.altitude as altitude, h.time_zone as time_zone, h.sky_quality as sky_quality," \
        "e.telName as telName, e.focalLength as focalLength, e.diameter as diameter, e.camName as camName, e.pixelSize as pixelSize, e.sensorW as sensorW, e.sensorH as sensorH," \
        "e.camera_type1 as camera_type1, e.camera_type2 as camera_type2, e.filterArray as filterArray, e.mountName as mountName, e.mount_type as mount_type, e.deg as deg," \
        "e.barlowName as barlowName, e.magnification as magnification, e.focalRatio as focalRatio, e.fovDeg as fovDeg, e.resolution as resolution, e.project_priority as priority, h.uhaveid as id" ,usr=usr).data()
    return user_equipments

#this function calculate the declination limit of the equipment and update the table
def update_declination(uhaveid):
    query_relation = "MATCH (x:user)-[h:UhaveE{uhaveid:$uhaveid}]->(e:equipments) return h.longitude as longitude, h.latitude as latitude, h.altitude as altitude, e.deg as deg"
    eq_info = graph.run(query_relation, uhaveid=uhaveid).data()

    dec_lim = declination.run(float(eq_info[0]['longitude']), float(eq_info[0]['latitude']), float(eq_info[0]['altitude']), float(eq_info[0]['deg']))

    query_update = "MATCH (x:user)-[h:UhaveE{uhaveid:$uhaveid}]->(e:equipments) set h.declination_limit=$dec_lim"
    graph.run(query_update, uhaveid=uhaveid, dec_lim=dec_lim)

#delete a user's equipment
def delete_user_equipment(usr: str,uhaveid: int):
    # delete the schedule first
    eid = get_eid(uhaveid)
    graph.run("MATCH (e:equipments {EID:$EID})-[r:EhaveS]->(s:schedule) DELETE r,s", EID=eid)
    # delete the project-equipment relationship
    graph.run("match (p:project)-[r:PhaveE]->(e:equipments{EID:$EID}) DELETE r", EID=eid)
    # delete user's equipment
    graph.run("MATCH (x:user {email:$usr})-[h:UhaveE {uhaveid: $uhaveid}]->(e:equipments) DELETE h,e", usr=usr, uhaveid=uhaveid)

# create a new interest target for user
def create_user_target(usr: str, TID: int):
    query = "match (x:user{email:$usr}) match (t:target{TID:$TID}) create (x)-[ult:ULikeT{uliketid:$uliketid}]->(t)"

    count = graph.run("MATCH ()-[ult:UlikeT]->() return ult.uliketid order by ult.uliketid DESC limit 1 ").data()
    if len(count) == 0:
        cnt = 0
    else:
        cnt = count[0]['ult.uliketid']+1
    print(TID, usr)

    graph.run(query, usr=usr, TID=TID, uliketid=cnt)

#delete a user's interest target
def delete_user_insterest(usr: str, TID: int):
    query = "match (x:user{email:$usr})-[r:ULikeT]->(t:target{TID:$TID}) delete r"
    graph.run(query, usr=usr, TID=TID)

#create a new equipment 
# def create_equipments(telName: str, focalLength: float, diameter: float,
#                     camName: str, pixelSize: float, sensorW: int, sensorH: int, camera_type1: str, camera_type2: str,
#                     lFilter: str, rFilter: str, gFilter: str, bFilter: str, haFilter: str, oiiiFilter: str, siiFilter: str, duoFilter: str, multispectraFilter: str,
#                     JohnsonU: str, JohnsonB: str, JohnsonV: str, JohnsonR: str, JohnsonI: str, SDSSu: str, SDSSg: str, SDSSr: str, SDSSi: str, SDSSz: str,
#                     mountName: str, mount_type, deg, barlowName, magnification,
#                     focalRatio, fovDeg, resolution):
def create_equipments(telName: str, focalLength: float, diameter: float,
                    camName: str, pixelSize: float, sensorW: float, sensorH: float, camera_type1: str, camera_type2: str, filterArray: list,
                    mountName: str, mount_type: str, deg: float, barlowName: str, magnification: float,
                    focalRatio: float, fovDeg: float, resolution: float):
    # create an equipment
    count = graph.run("MATCH (e:equipments) return e.EID  order by e.EID DESC limit 1 ").data()
    
    equipment = Equipments()
    if len(count) == 0:
        equipment.EID = 0
    else:
        equipment.EID = count[0]['e.EID']+1
    equipment.telName = telName
    equipment.focalLength = focalLength
    equipment.diameter = diameter
    equipment.camName = camName
    equipment.pixelSize =pixelSize
    equipment.sensorW = sensorW
    equipment.sensorH = sensorH
    equipment.camera_type1 = camera_type1
    equipment.camera_type2 = camera_type2
    # equipment.lFilter = lFilter
    # equipment.rFilter = rFilter
    # equipment.sensorW = gFilter
    # equipment.sensorW = bFilter
    # equipment.haFilter = haFilter
    # equipment.oiiiFilter = oiiiFilter
    # equipment.siiFilter = siiFilter
    # equipment.duoFilter = duoFilter
    # equipment.multispectraFilter = multispectraFilter
    # equipment.JohnsonU = JohnsonU
    # equipment.JohnsonB = JohnsonB
    # equipment.JohnsonV = JohnsonV
    # equipment.JohnsonR = JohnsonR
    # equipment.JohnsonI = JohnsonI
    # equipment.SDSSu = SDSSu
    # equipment.SDSSg = SDSSg
    # equipment.SDSSr = SDSSr
    # equipment.SDSSi = SDSSi
    # equipment.SDSSz = SDSSz
    equipment.filterArray = filterArray
    equipment.mountName = mountName
    equipment.mount_type = mount_type
    equipment.deg = deg
    equipment.barlowName = barlowName
    equipment.magnification = magnification
    equipment.focalRatio = focalRatio
    equipment.fovDeg = fovDeg
    equipment.resolution = resolution
    equipment.project_priority = []
    graph.create(equipment)
    
    return equipment



'''def get_equipments(usr:str)->Optional[Equipments]:
    
    equipment = graph.run("MATCH (x:usrr {email:$usr})-[h:have_e]->(e:equipment) return e.EID as eid, e.aperture as aperture, e.Fov as Fov, e.pixel_scale as pixel_scale," \
                           "e.tracking_accuracy as  tracking_accuracy, e.lim_magnitude as lim_magnotude, e.elevation_lim as elevation_lim, e.mount_type as mount_type, e.camera_type1 as camer_type1," \
                           "e.camera_type2 as camera_type2, e.JohnsonB as JohnsonB, e.JohnsonR as JohnsonR, e.JohnsonV as JohnsonV, e.SDSSu as SDSSu, e.SDSSg as SDSSg, e.SDSSr as SDSSr, e.SDSSi as SDSSi," \
                           "e.SDSSz as SDSSz", usr = usr).data()
    print(equipment)
    return equipment  
'''   


#get the equipment id
def get_eid(uhaveid):
    query_eid = "MATCH (x:user)-[h:UhaveE{uhaveid:$uhaveid}]->(e:equipments) return e.EID as EID"
    eid = graph.run(query_eid, uhaveid=uhaveid).data()

    eid = int(eid[0]['EID'])

    return eid


def update_equipment_project_priority(usr: str, eid : int, project_priority: list):
    print(project_priority)
    query = "MATCH x = (e:equipments{EID:$eid}) set e.project_priority = $project_priority"
    result = graph.run(query, eid = eid, project_priority = project_priority)

def get_equipment_project_priority(usr:str,eid : int):
    query = "MATCH (x:user{email:$usr})-[h:UhaveE]->(e:equipments{EID:$eid}) return e.project_priority as priority"
    result = graph.run(query,usr = usr,eid = eid).data()
    print(eid, " Result: ", result)
    if(len(result) == 0 ): 
        return None
    else :
        return result[0]['priority']