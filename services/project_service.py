from data.db_session import db_auth
from typing import Optional
from services.classes import User, Target, Equipments, Project, Schedule
from datetime import datetime, timedelta
from services.accounts_service import get_equipment_project_priority, update_equipment_project_priority
from services.utils import *

import astro.declination_limit_of_location as declination
import astro.astroplan_calculations as schedule
import astro.nighttime_calculations as night
import random
import threading

graph = db_auth()

FILTER = ['lFilter','rFilter','gFilter','bFilter','haFilter','oiiiFilter','siiFilter','duoFilter','multispectraFilter', \
            'JohnsonU','JohnsonB','JohnsonV','JohnsonR','JohnsonI',\
            'SDSSu','SDSSg','SDSSr','SDSSi','SDSSz']

# Y
def get_project_info(pid_list : list):
    project = []
    for pid in pid_list:
        info = get_project_detail(pid)
        project.append(info[0])

    return project

# Y get a project's information
def get_project_detail(PID: int):
    #get the project's detail
    query = "MATCH (n:project {PID: $PID})" \
    "return n.project_type as project_type, n.title as title, n.PI as PI, n.description as description, n.FoV_lower_limit as FoV_lower_limit, n.resolution_upper_limit as resolution_upper_limit, " \
    "n.required_camera_type as required_camera_type, n.required_filter as required_filter, n.PID as PID"
    project = graph.run(query, PID = PID).data()

    for p in project:
        for i, filter in enumerate(FILTER):
            p[filter] = p['required_filter'][i] if p['required_filter'] is not None else False
        p['percentage'], _ = get_progress_percentage(int(p['PID']))

    return project

# Y this function will return project which user can join (equipment based)
def get_project(usr: str)->Optional[Project]:
    # get all the user's equipment
    query = "MATCH (x:user {email:$usr})-[rel:UhaveE]->(e:equipments) " \
        "return e.EID as EID, e.camera_type1 as camera_type1, e.filterArray as filterArray, e.fovDeg as fovDeg, e.resolution as resolution"
    equipment = graph.run(query, usr = usr).data()

    # get all the currenet projects in DB
    query = "MATCH (n:project) return n.project_type as project_type, n.title as title, n.description as description," \
        "n.FoV_lower_limit as FoV_lower_limit, n.resolution_upper_limit as resolution_upper_limit," \
        "n.required_camera_type as required_camera_type, n.required_filter as required_filter, n.PID as PID order by PID" 
    project = graph.run(query).data()

    # get the project which user has already joined
    query = "match (x:user{email:$usr})-[r:Member_of]->(p:project) return p.PID as PID"
    joined = graph.run(query,usr =usr).data()
    pid_list = []
    for i in range(len(joined)):
        pid_list.append(joined[i]['PID'])
    
    # filter project
    result = []
    for i in range(len(equipment)):
        for j in range(len(project)):
            if project[j]['PID'] in result: continue
            if any(pid == project[j]['PID'] for pid in pid_list): continue
            if float(equipment[i]['fovDeg']) < project[j]['FoV_lower_limit']: continue
            if float(equipment[i]['resolution']) > project[j]['resolution_upper_limit']: continue
            # equipment_camera_type = 0 if equipment[i]['camera_type1'] == 'colored' else 1
            if project[j]['required_camera_type'] != equipment[i]['camera_type1']: continue
            # if no filter is required
            if sum(project[j]['required_filter']) == 0:
                n = graph.run("MATCH (x:user{email: $usr}) return x.name as manager_name",usr = usr).data()
                project[j]['manager_name'] = n[0]['manager_name']
                result.append(project[j])
            elif any(equipment[i]['filterArray'][k] + project[j]['required_filter'][k] == 2 for k in range(19)):
                # print(project[j])
                n = graph.run("MATCH (x:user{email: $usr}) return x.name as manager_name",usr = usr).data()
                project[j]['manager_name'] = n[0]['manager_name']
                result.append(project[j]) 

    # result = get_project_filter(usr, result)
    for p in result:
        for i, filter in enumerate(FILTER):
            p[filter] = p['required_filter'][i] if p['required_filter'] is not None else False
        p['percentage'], _ = get_progress_percentage(int(p['PID']))

    return result

# Y search a project by keyword
def search_project(text: str):
    query= "MATCH (p:project) where p.name =~ $text return p.PID as PID, p.name as name order by p.name limit 20"
    project = graph.run(query, text=text).data()
    print(project)

    return project

def get_join_status(usr, PID):
    query = "MATCH (n:user{email:$usr}), (p:project{PID:$PID}) RETURN exists((n)-[:Member_of]-(p))"
    
    return graph.run(query, usr=usr, PID=PID)

'''
# N choose the project with user's interested targets (interest based)
def get_project_filter(usr: str, project_list: list):
    random.shuffle(project_list)
    interest = get_user_interest(usr)

    chosen_project = []

    find = 0
    for project in project_list:
        find = 0
        project_target = get_project_target(project['PID'])
        for t in project_target:
            for i in interest:
                if i['TID'] == t['TID']:
                    chosen_project.append(project)
                    find = 1
                    break
            if len(chosen_project) > 10 or find == 1:
                break
        if len(chosen_project) > 10 or find == 1:
            break

    plen = len(project_list)
    if plen < 10:
        goal = plen
    else:
        goal = 10

    # if the total of chosen projects is less than 10 or goal, random append projects to the list
    exist = 0
    if len(chosen_project) < goal:
        for i in range(goal-len(chosen_project)):
            while True:
                exist = 0
                rand_index = random.randint(0, plen-1)
                rand_pid = project_list[rand_index]['PID']
                for chosen in chosen_project:
                    if chosen['PID'] == rand_pid:
                        exist = 1
                        break
                if exist == 0:
                    break
            chosen_project.append(project_list[rand_index])

    return chosen_project
'''

# Y 0331 rank joined projects
def get_project_default_priority(projects):
    ranked_projects = sorted(projects, key=lambda k:k['project_type'], reverse=True)

    return ranked_projects

# Y get a project observe target
def get_project_target(pid: int):
    # consider to delete the targets that have reached the goal of observe time
    query = "MATCH x=(p:project{PID:$pid})-[r:PHaveT]->(t:target) RETURN t.name as name, t.latitude as lat, t.longitude as lon, t.TID as TID"
    project_target = graph.run(query, pid=pid).data()
    for target in project_target:
        target['ra'], target['dec'] = degree2hms(target['lon'], target['lat'], _round=True)

    return project_target

'''
# N get a project equipment's target list
def get_project_equipment_TargetList(pid: int, eid: int):
    # consider to delete the targets that have reached the goal of observe time
    query = "MATCH x=(p:project{PID:$pid})-[r:PHaveE]->(e:Equipment{EID:$eid}) RETURN r.target_list as target_list"
    project_target = graph.run(query, pid=pid, eid=eid).data()

    return project_target[0]['target_list']
'''

# Y create a new project
def create_project(usr, project_type, title, description, FoV_lower_limit, resolution_upper_limit, required_camera_type, required_filter)->Optional[Project]:
    #this function will create a project  
    count = graph.run("MATCH (p:project) return p.PID  order by p.PID DESC limit 1 ").data()
    project = Project()
    if len(count) == 0:
        project.PID = 0
    else:
        project.PID = count[0]['p.PID']+1
    project.project_type = project_type
    project.title = title
    tmp = graph.run("MATCH (x:user {email: $usr})  return x.UID", usr = usr).data()
    project.PI = tmp[0]['x.UID']
    project.description = description
    project.FoV_lower_limit = FoV_lower_limit
    project.resolution_upper_limit = resolution_upper_limit
    project.required_camera_type = required_camera_type
    project.required_filter = required_filter
    graph.create(project)

    query = "MATCH (x:user {email: $usr}) MATCH (p:project {PID: $PID}) create (x)-[m:Manage {umanageid:$umanageid}]->(p)"
    count = graph.run("MATCH ()-[m:Manage]->() return m.umanageid  order by m.umanageid DESC limit 1").data()
    if len(count) == 0:
        cnt = 0
    else:
        cnt = count[0]['m.umanageid']+1
    graph.run(query, usr = usr, PID = project.PID,umanageid = cnt)

    return project

# Y update a project's information
def update_project(usr: str, PID: int, umanageid: int, project_type: str, title: str, description: str,
                FoV_lower_limit: float, resolution_upper_limit: float, required_camera_type: list, required_filter: list)->Optional[Project]:
    # print(PID)
    # print(umanageid)
    # print(usr)
    query ="MATCH rel = (x:user)-[p:Manage {umanageid: $umanageid}]->(m:project) return rel"
    # print(graph.run(query, usr=usr, umanageid=umanageid).data())

    query ="MATCH (x:user {email:$usr})-[p:Manage {umanageid: $umanageid}]->(m:project)" \
            "set m.project_type=$project_type, m.title=$title, m.description=$description," \
            "m.FoV_lower_limit=$FoV_lower_limit, m.resolution_upper_limit=$resolution_upper_limit," \
            "m.required_camera_type=$required_camera_type, m.required_filter=$required_filter" 

    project = graph.run(query, usr=usr, umanageid=umanageid, project_type=project_type, title=title, description=description, FoV_lower_limit=FoV_lower_limit, resolution_upper_limit=resolution_upper_limit, required_camera_type=required_camera_type, required_filter=required_filter).data()

    return project   

# Y delete a project
def delete_project(usr: str, PID: int, umanageid: int):
    graph.run("MATCH (p:project {PID:$PID})-[r:PHaveT]->(t:target) DELETE r", PID=PID)
    # delete project priority in equipment's attribute
    equipment = graph.run("MATCH (p:project {PID:$PID})-[r:PhaveE]->(e:equipments) RETURN e.EID as eid, e.project_priority as pp", PID=PID).data()
    for e in equipment:
        pp = e['pp']
        pp.remove(PID)
        graph.run("MATCH x = (e:equipments{EID:$eid}) set e.project_priority = $project_priority", eid=e['eid'], project_priority=pp)
    graph.run("MATCH (p:project {PID:$PID})-[r:PhaveE]->(e:equipments) DELETE r", PID=PID)
    graph.run("MATCH (n:user {email:$usr})-[r:Member_of]->(p:project {PID:$PID}) DELETE r", usr=usr, PID=PID)
    graph.run("MATCH (x:user {email:$usr})-[m:Manage {umanageid: $umanageid}]->(p:project) DELETE m, p", usr=usr, umanageid=umanageid)

# Y get the project's manager
def get_project_manager_name(PID: int):
    query = "MATCH (p:project {PID: $PID}) return p.PI as PI"
    result = graph.run(query,PID = PID).data()
    query = "MATCH (x:user {UID: $UID}) return x.name as name, x.affiliation as affiliation, x.title as title"
    manager_name = graph.run(query, UID = result[0]['PI']).data()

    return manager_name

'''
# N add a new project manager to a project
def add_project_manager(usr: str, PID: int):
    query = "MATCH (x:user {email: $usr}) MATCH (p:project {PID: $PID}) create (x)-[m:Manage {umanageid:$umanageid}]->(p)"
    count = graph.run("MATCH ()-[m:Manage]->() return m.umanageid  order by m.umanageid DESC limit 1 ").data()
    if len(count) == 0:
        cnt = 0
    else:
        cnt = count[0]['m.umanageid']+1
    graph.run(query, usr=usr, PID=PID, umanageid=cnt)

    return
'''

# Y get the project list of a project manager
def user_manage_projects_get(usr: str):
    # return the project user manage 
    query="MATCH (x:user {email:$usr})-[m:Manage]->(p:project) return m.umanageid as umanageid, p.project_type as project_type, p.title as title," \
        "p.PI as PI, p.description as description, p.FoV_lower_limit as FoV_lower_limit, p.resolution_upper_limit as resolution_upper_limit," \
        "p.required_camera_type as camera_type1, p.required_filter as required_filter, p.PID as PID"
    project = graph.run(query,usr = usr).data()
    
    for p in project:
        for i, filter in enumerate(FILTER):
            p[filter] = p['required_filter'][i] if p['required_filter'] is not None else False
        p['percentage'], _ = get_progress_percentage(int(p['PID']))
        
    return project

# Y add a new target to project
def create_project_target(usr: str, PID: int, TID: int, filter2observe: list, time2observe: list, mode: int):
    query="MATCH (p:project {PID:$PID}) MATCH (t:target {TID:$TID}) create (p)-[pht:PHaveT {phavetid:$phavetid, Filter_to_Observe:$filter2observe, Time_to_Observe:$time2observe, Remain_to_Observe:$remain2observe, Mode:$mode}]->(t) return pht.phavetid"
    # only show the observable targets of that equipment
    # update_project_equipment_observe_list(usr, PID, TID, JohnsonB, JohnsonR, JohnsonV, SDSSu, SDSSg, SDSSr, SDSSi, SDSSz)
    count = graph.run("MATCH ()-[pht:PHaveT]->() return pht.phavetid  order by pht.phavetid DESC limit 1 ").data()
    if len(count) == 0:
        cnt = 0
    else:
        cnt = count[0]['pht.phavetid']+1
    result = graph.run(query, PID = PID, TID = TID, phavetid = cnt, filter2observe = filter2observe, time2observe = time2observe, remain2observe = time2observe, mode = mode).data()
    print("RESULT", result)

    return result

# Y 0107 edit project target
def update_project_target(PID: int, TID: int, filter2observe: list, time2observe: list, mode: int):
    query ="MATCH (p:project {PID:$PID})-[r:PHaveT]->(t:target {TID: $TID})" \
            "set r.Filter_to_Observe=$filter2observe, r.Time_to_Observe=$time2observe, r.Remain_to_Observe=$time2observe, r.Mode=$mode"
    result = graph.run(query, PID=PID, TID=TID, filter2observe=filter2observe, time2observe=time2observe, mode=mode).data()

    return result

# Y 0107 delete project target
def delete_project_target(PID: int, TID: int):
    graph.run("MATCH (p:project {PID:$PID})-[r:PHaveT]->(t:target {TID: $TID}) DELETE r", PID=PID, TID=TID)

# Y 1221 get project / project target progress (percentage)
def get_progress_percentage(PID: int):
    query = "MATCH (p:project {PID:$PID})-[r:PHaveT]->(t:target) return r.Filter_to_Observe as f2o, r.Time_to_Observe as t2o, r.Remain_to_Observe as r2o, r.Mode as mode, t.TID as TID, t.name as name, t.latitude as lat, t.longitude as lon"
    target_progress = graph.run(query, PID=PID).data()

    # calculate entire project progress
    project_total_t2o = 0
    project_total_r2o = 0
    target_progress_percentage = []
    for t in target_progress:
        t_t2o = sum(t['t2o'])
        t_r2o = sum(t['r2o'])
        t_TID = t['TID']
        t_percent = (t_t2o-t_r2o) / t_t2o if t_t2o is not 0 else 100
        project_total_t2o += t_t2o
        project_total_r2o += t_r2o
        hms, dms = degree2hms(t['lon'], t['lat'], _round=True)
        f2o = {}
        for i, f in enumerate(FILTER):
            f2o[f] = t['f2o'][i]
            f2o[f.replace("Filter", "")+"Min"] = t['t2o'][i]
        f2o['mode'] = t['mode']
        target_progress_percentage.append({'TID': t_TID, 'name': t['name'], 'filter': f2o, 'lat': t['lat'], 'lon': t['lon'], 'lat_dms': dms, 'lon_hms': hms, 'percentage': t_percent})

    project_progress_percentage = (project_total_t2o-project_total_r2o) / project_total_t2o if project_total_t2o is not 0 else 100

    return project_progress_percentage, target_progress_percentage

# Y 1214 return the qualified equipments when join a project
def get_qualified_equipment(usr: str, PID: int):
    query_eid = "MATCH (x:user{email:$usr})-[r:UhaveE]->(e:equipments) RETURN e.EID as EID, e.telName as telName, e.fovDeg as fovDeg, e.resolution as resolution, e.filterArray as filterArray, e.camera_type1 as camera_type1, r.declination_limit as declination"
    equipment = graph.run(query_eid, usr=usr).data()
    # project_target = graph.run("MATCH (p:project {PID: $PID})-[pht:PHaveT]->(t:target) return pht.filter2observe as filter2observe, t.TID as TID, t.name as name, t.latitude as dec", PID=PID).data()
    project = graph.run("MATCH (p:project {PID: $PID}) return p.FoV_lower_limit as FoV_lower_limit, p.resolution_upper_limit as resolution_upper_limit, p.required_camera_type as required_camera_type, p.required_filter as required_filter", PID=PID).data()
    
    qualified_eid_list, qualified_equipment_list = [], []
    for i in range(len(equipment)):
        if float(equipment[i]['fovDeg']) < project[0]['FoV_lower_limit']: continue
        if float(equipment[i]['resolution']) > project[0]['resolution_upper_limit']: continue
        # equipment_camera_type = 0 if equipment[i]['camera_type1'] == 'colored' else 1
        if project[0]['required_camera_type'] != equipment[i]['camera_type1']: continue
        # if no filter is required
        if sum(project[0]['required_filter']) == 0:
            qualified_equipment_list.append({'EID': int(equipment[i]['EID']), 'telName': equipment[i]['telName']})
            qualified_eid_list.append(int(equipment[i]['EID']))
        elif any(equipment[i]['filterArray'][k] + project[0]['required_filter'][k] == 2 for k in range(19)):
            qualified_equipment_list.append({'EID': int(equipment[i]['EID']), 'telName': equipment[i]['telName']})
            qualified_eid_list.append(int(equipment[i]['EID']))

    return qualified_eid_list, qualified_equipment_list

# Y this function is uesd for test, the user will auto join the project (1214 modified)
def auto_join(usr: str, PID: int, selected_eid_list: list):
    # check if already joined the project 
    query = "MATCH (x:user {email:$usr})-[r]->(p:project{PID:$PID})  return exists((x)-[:Member_of]->(p)) as flag"
    exist = graph.run(query, usr=usr, PID=PID).data()
    if exist and exist[0]['flag']:
        print("exist")
        return
    
    # create user-project relationship
    query = "MATCH (x:user {email:$usr}) MATCH (p:project {PID:$PID})  create (x)-[:Member_of {memberofid: $memberofid, join_time: $join_time}]->(p)"
    time = graph.run("return datetime() as time").data() 
    count = graph.run("MATCH ()-[rel:Memberof]->() return rel.memberofid  order by rel.memberofid DESC limit 1 ").data()
    time = graph.run("return datetime() as time").data() 
    if len(count) == 0:
        cnt = 0
    else:
        cnt = count[0]['rel.memberofid']+1
    graph.run(query, usr=usr, PID=PID, memberofid=cnt, join_time=time[0]['time'])

    # create equipment-project relationship
    # qualified_eid_list = get_qualified_equipment(usr, PID)
    # get the information of selected equipments
    query_eqInfo = "MATCH (x:user {email:$usr})-[r:UhaveE]->(e:equipments {EID:$EID}) return r.declination_limit as declination"
    query_createPE = "MATCH (p:project {PID:$PID}) MATCH (e:equipments {EID:$EID}) CREATE (p)-[rel:PhaveE {phaveeid:$phaveeid, declination_limit: $declination}]->(e)"
    for eid in selected_eid_list:
        count = graph.run("MATCH ()-[rel:PhaveE]->() return rel.phaveeid order by rel.phaveeid DESC limit 1").data()
        if len(count) == 0:
            cnt = 0
        else:
            cnt = count[0]['rel.phaveeid']+1
        
        # target_list = initial_equipment_target_list(usr, eid, PID)
        declination = graph.run(query_eqInfo, usr=usr, EID=eid).data()
        graph.run(query_createPE, PID=PID, EID=eid, phaveeid=cnt, declination=declination[0]['declination'])
        
        # add the project to the last in the priority list
        old_priority = get_equipment_project_priority(usr, eid)
        print("priority", old_priority)
        if(old_priority == None):
            pidlist = []
            pidlist.append(PID)
            print("eid", eid)
            print("append ", pidlist)
            update_equipment_project_priority(usr, eid, pidlist)
        else:
            old_priority.append(PID)
            update_equipment_project_priority(usr, eid, old_priority)

# this function is used to test, the user will auto leave the project
def auto_leave(usr: str, PID: int):
    # delete user-project relationship
    query_user_bye = "MATCH (x:user {email:$usr})-[rel:Member_of]->(p:project{PID:$PID}) delete rel"
    graph.run(query_user_bye, usr=usr, PID=PID)

    # delete project-equipment relationship
    qualified_eid_list = get_qualified_equipment(usr, PID)
    query_equipment_bye = "MATCH (p:project {PID:$PID})-[rel:PhaveE]->(e:equipments{EID:$EID}) delete rel"
    
    for i in range(len(qualified_eid_list)):
        graph.run(query_equipment_bye, PID=PID, EID=qualified_eid_list[i])


def apply_project(usr: str,PID: int)->int:
    # this function will create an apply_to relationship to the project
    # return value
    # 1 : apply success

    query = "MATCH (x:user {email:$usr}) MATCH (p:project {PID:$PID})  create (x)-[:Apply_to {applyid: $applyid, status: $status, apply_time: $apply_time}]->(p)"
    time = graph.run("return datetime() as time").data() 
    count = graph.run("MATCH ()-[apply:Apply_to]->() return apply.applyid  order by apply.applyid DESC limit 1 ").data()
    if len(count) == 0:
        cnt = 0
    else:
        cnt = count[0]['apply.applyid']+1
    graph.run(query, usr = usr, PID = PID, applyid = cnt,status ='waiting', apply_time = time[0]['time'])

    return 1

def apply_project_status(usr: str, PID: int)->int:
    # this function will chechk whether user apply to the project or not 
    # 0 : error
    # 1 : no 
    # 2 : yes, waiting
    # 3 : yes, already join
    query = "MATCH (x:user {email:$usr})-[rel:Apply_to]->(p:project {PID:$PID}) return rel.status "
    result = graph.run(query, usr = usr, PID = PID).data()
    

    if len(result) == 0 or result[len(result)-1] == 'reject':
        return 1
    elif result[len(result)-1]['rel.status'] == 'accept':
        return 3
    elif result[len(result)-1]['rel.status'] == 'waiting':
        return 2
    else:
        return 0

def get_apply_waiting(usr: str):
    # this function will return the list of user's applied project which status is waiting
    query = "MATCH (x:user {email:$usr})-[:Apply_to {status: $status}]->(p:project) return p.PID as PID"
    waitiing_list = graph.run(query, usr = usr, status = 'waiting').data()
    return waitiing_list

def get_apply_history(usr: str):
    # this function will return the apply history of an user 
    query = "MATCH (x:user {email:$usr})-[rel:Apply_to]->(p:project) return p.PID as PID, rel.status as status, p.title as title, rel.apply_time as time"
    apply_history = graph.run(query, usr = usr).data()
    print(apply_history)
    return apply_history

def get_want_to_join_project(usr: str, PID : int):
    # project manage can get ther list of who want to join his project
    query = "MATCH (x:user)-[rel:Apply_to {status: $status}]->(p:project {PID: $PID}) return x.name as name, rel.applyid as applyid, rel.time as time "
    apply_list = graph.run(query, status = 'waiting', PID = PID).data()
    return apply_list

def reject_join_project(usr: str, PID: int, UID: int, applyid: int):
    # reject user'apply
    # 1 : success, 0: error
    query = "MATCH (x:user {email: $UID})-[rel:Apply_to {applyid: $applyid}]->(p:project {PID: $PID}) SET rel.status = $status return  rel.status as status"
    result = graph.run(query, status = 'reject', PID = PID, UID = UID, applyid = applyid).data()
    if len(result) == 1  and result[0]['status'] == 'reject':
        return 1
    else:
        return 0

def accept_join_project(usr: str, PID: int, UID: int, applyid: int):
    # accept a user'apply
    query = "MATCH (x:user {email: $UID})-[rel:Apply_to {applyid: $applyid}]->(p:project {PID: $PID}) SET rel.status = $status return  rel.status as status"
    result = graph.run(query, status = 'accept', PID = PID, UID = UID, applyid = applyid).data()
    if len(result) == 1  and result[0]['status'] == 'accept':
        
        query = "CREATE (x:user {email: $UID})-[rel: Member_of {memberofid: $memberofid}]->(p:project {PID: $PID})"
        count = graph.run("MATCH ()-[rel:Memberof]->() return rel.memberofif  order by rel.memberofid DESC limit 1 ").data()
        if len(count) == 0:
            cnt = 0
        else:
            cnt = count[0]['rel.memberofid']+1
        graph.run(query, UID = UID, PID =PID, memberofid = cnt)
        return 1
    else:
        return 0

# return the user in this project
def get_project_member(usr: str, PID: int):
    query = "MATCH (x:user)-[rel:Member_of]->(p:project {PID: $PID}) return  x.name as name"
    member = graph.run(query, PID =PID).data()
    return member

# Y return the equipments in this project
def get_project_equipment(PID: int):
    query = "MATCH (p:project {PID:$PID})-[rel:PhaveE]->(e:equipments) return e.EID as eid," \
        "e.telName as telName, e.focalLength as focalLength, e.diameter as diameter, e.camName as camName, e.pixelSize as pixelSize, e.sensorW as sensorW, e.sensorH as sensorH," \
        "e.camera_type1 as camera_type1, e.camera_type2 as camera_type2, e.filterArray as filterArray, e.mountName as mountName, e.mount_type as mount_type, e.deg as deg," \
        "e.barlowName as barlowName, e.magnification as magnification, e.focalRatio as focalRatio, e.fovDeg as fovDeg, e.resolution as resolution, rel.declination_limit as declination"
    eq_list = graph.run(query, PID=PID).data()
    return eq_list

# get all the project user have already joined
def get_project_join(usr: str):
    query = "MATCH (x:user {email:$usr})-[rel:Member_of]->(p:project) return p.project_type as project_type, p.title as title, p.PI as PI, p.description as description," \
        "p.FoV_lower_limit as FoV_lower_limit, p.resolution_upper_limit as resolution_upper_limit, p.required_camera_type as required_camera_type, p.required_filter as required_filter, p.PID as PID order by PID"
    join_list = graph.run(query, usr = usr).data()
    if  len(join_list) == 0: 
        return None
    return  join_list

'''
# return the project based on user's equipment 
def get_project_join_filter(projectlist: list,usr: str,uhaveid: int):
    equipment = graph.run("MATCH (x:user{email: $usr})-[:UhaveE{uhaveid:$uhaveid}]->(e:equipments) " \
        " return e.EID as EID,e.JohnsonB as jb,e.JohnsonV as jv, e.JohnsonR as jr, e.SDSSu as su, e.SDSSg as sg, e.SDSSr as sr , e.SDSSi as si, e.SDSSz as sz" \
        ",e.mount_type as mount_type, e.camera_type1 as camera_type1, e.camera_type2 as camera_type2" ,usr = usr , uhaveid = uhaveid).data()
    
    result = []
    for j in range(len(projectlist)):
        if projectlist[j]['PID'] in result: continue

        p = get_project_detail(projectlist[j]['PID'])

        if equipment[0]['jb'] == 'n':
            if p[0]['JohnsonB'] == 'y': continue
        if equipment[0]['jv'] == 'n':
            if p[0]['JohnsonV'] == 'y': continue
        if equipment[0]['jr'] == 'n':
            if p[0]['JohnsonR'] == 'y': continue
        if equipment[0]['su'] == 'n':
            if p[0]['SDSSu'] == 'y': continue
        if equipment[0]['sg'] == 'n':
            if p[0]['SDSSg'] == 'y': continue
        if equipment[0]['sr'] == 'n':
            if p[0]['SDSSr'] == 'y': continue
        if equipment[0]['si'] == 'n':
            if p[0]['SDSSi'] == 'y': continue
        if equipment[0]['sz'] == 'n':
            if p[0]['SDSSz'] == 'y': continue
        if equipment[0]['mount_type'] != p[0]['mount_type']: continue
        if equipment[0]['camera_type1'] != p[0]['camera_type1']: continue
        if equipment[0]['camera_type2'] != p[0]['camera_type2']: continue
        result.append(projectlist[j])

    return result

def fliter_project_target(usr: str, PID: int):
    #return the target based on user's equipment 
    query = "MATCH (x:user {email:$usr})-[rel:UhaveE]->(e:equipments)" \
        " return e.EID as EID,e.mount_type as mount_type, e.camera_type1 as camera_type1, e.camera_type2 as camera_type2,e.JohnsonB as jb,e.JohnsonV as jv, e.JohnsonR as jr, e.SDSSu as su, e.SDSSg as sg, e.SDSSr as sr , e.SDSSi as si, e.SDSSz as sz, rel.declination_limit as declination"
    equipment = graph.run(query, usr = usr).data()
    #query = "MATCH (x:user {email:$usr})-[rel:UhaveE]->(e:equipments), (n:project {PID: $PID}) where n.mount_type=e.mount_type and n.camera_type1=e.camera_type1 and n.camera_type2=e.camera_type2 " \
    #   "and n.JohnsonB=e.JohnsonB and n.JohnsonV=e.JohnsonV and n.JohnsonR=e.JohnsonR  and n.SDSSu=e.SDSSu  and n.SDSSg=e.SDSSg and n.SDSSr=e.SDSSr and n.SDSSi=e.SDSSi and n.SDSSz=e.SDSSz" \
    #    " return e.EID as EID,e.JohnsonB as jb,e.JohnsonV as jv, e.JohnsonR as jr, e.SDSSu as su, e.SDSSg as sg, e.SDSSr as sr , e.SDSSi as si, e.SDSSz as sz"
    #equipment = graph.run(query, usr = usr, PID = PID).data()
    project_target = graph.run("MATCH (p:project {PID: $PID})-[pht:PHaveT]->(t:target) " \
        " return pht.JohnsonB as JohnsonB, pht.JohnsonV as JohnsonV, pht.JohnsonR as JohnsonR, pht.SDSSu as SDSSu, pht.SDSSg as SDSSg, pht.SDSSr as SDSSr , pht.SDSSi as SDSSi, pht.SDSSz as SDSSz"
    ", t.TID as TID, t.name as name, t.latitude as lat, t.longitude as lon", PID = PID).data()
    print(len(equipment))
    print(len(project_target))
    target = []
    # filter with equipment capability
    for i in range(len(equipment)):
        for j in range(len(project_target)):
            if any(d['TID'] == project_target[j]['TID'] for d in target): continue
            if equipment[i]['jb'] == 'n':
                if project_target[j]['JohnsonB'] == 'y': continue
            if equipment[i]['jv'] == 'n':
                if project_target[j]['JohnsonV'] == 'y': continue
            if equipment[i]['jr'] == 'n':
                if project_target[j]['JohnsonR'] == 'y': continue
            if equipment[i]['su'] == 'n':
                if project_target[j]['SDSSu'] == 'y': continue
            if equipment[i]['sg'] == 'n':
                if project_target[j]['SDSSg'] == 'y': continue
            if equipment[i]['sr'] == 'n':
                if project_target[j]['SDSSr'] == 'y': continue
            if equipment[i]['si'] == 'n':
                if project_target[j]['SDSSi'] == 'y': continue
            if equipment[i]['sz'] == 'n':
                if project_target[j]['SDSSz'] == 'y': continue
            # filter with equipment declination limit
            if float(equipment[i]['declination']) <= 0 and float(project_target[j]['lat']) < float(equipment[i]['declination']):
                continue
            if float(equipment[i]['declination']) > 0 and float(project_target[j]['lat']) > float(equipment[i]['declination']):
                continue

            target.append(project_target[j])
    print(len(target))

    return target

# Update the equipment target list when add new target to project
def update_project_equipment_observe_list(usr: str, PID: int, TID: int, JohnsonB: str, JohnsonR: str, JohnsonV: str,SDSSu: str,SDSSg: str,SDSSr: str,SDSSi: str,SDSSz: str):
    target_lat = graph.run("MATCH(t:target{TID:$TID}) return t.latitude as lat", TID = TID).data()
    
    eq_list = get_project_equipment(PID)
    if len(eq_list) == 0:
        return 0
    else :
        for i in range(len(eq_list)):
            if eq_list[i]['JohnsonB'] == 'n':
                if JohnsonB == 'y': continue
            if eq_list[i]['JohnsonV'] == 'n':
                if JohnsonV == 'y': continue
            if eq_list[i]['JohnsonR'] == 'n':
                if JohnsonR == 'y': continue
            if eq_list[i]['SDSSu'] == 'n':
                if SDSSu == 'y': continue
            if eq_list[i]['SDSSg'] == 'n':
                if SDSSg == 'y': continue
            if eq_list[i]['SDSSr'] == 'n':
                if SDSSr == 'y': continue
            if eq_list[i]['SDSsi'] == 'n':
                if SDSSi == 'y': continue
            if eq_list[i]['SDSSz'] == 'n':
                if SDSSz == 'y': continue

            # filter with equipment declination limit
            if float(eq_list[i]['declination']) <= 0 and float( target_lat[0]['lat']) < float(eq_list[i]['declination']):
                continue
            if float(eq_list[i]['declination']) > 0 and float( target_lat[0]['lat']) > float(eq_list[i]['declination']):
                continue
            
            query = "MATCH (p:project {PID: $PID})-[rel:PHaveE]->(e:equipment{EID:$EID}) return rel.target_list as list"
            target_list = graph.run(query).data()
            target_list.append(TID)
            query = "MATCH (p:project {PID: $PID})-[rel:PHaveE]->(e:equipment{EID:$EID}) set rel.target_list={target_list:$target_list} "
            graph.run(query, PID = PID, EID = eq_list[i]['eid'], target_list = target_list)

# initial a equipment target list when create project_equipment relationship
def initial_equipment_target_list(usr: str, EID: int, PID: int):
    project_target = graph.run("MATCH (p:project {PID: $PID})-[pht:PHaveT]->(t:target) " \
        " return pht.JohnsonB as JohnsonB, pht.JohnsonV as JohnsonV, pht.JohnsonR as JohnsonR, pht.SDSSu as SDSSu, pht.SDSSg as SDSSg, pht.SDSSr as SDSSr , pht.SDSSi as SDSSi, pht.SDSSz as SDSSz"
    ", t.TID as TID, t.name as name, t.latitude as lat, t.longitude as lon", PID = PID).data()

    query_eid = "MATCH (x:user{email:$usr})-[r:UhaveE]->(e:equipments{EID:$EID}) RETURN e.EID as EID, e.JohnsonB as jb,e.JohnsonV as jv, e.JohnsonR as jr, e.SDSSu as su, e.SDSSg as sg, e.SDSSr as sr , e.SDSSi as si, e.SDSSz as sz, r.declination_limit as declination"
    equipment = graph.run(query_eid, usr=usr,EID=EID).data()

    target = list()
    for j in range(len(project_target)):
        if equipment[0]['jb'] == 'n':
            if project_target[j]['JohnsonB'] == 'y': continue
        if equipment[0]['jv'] == 'n':
            if project_target[j]['JohnsonV'] == 'y': continue
        if equipment[0]['jr'] == 'n':
            if project_target[j]['JohnsonR'] == 'y': continue
        if equipment[0]['su'] == 'n':
            if project_target[j]['SDSSu'] == 'y': continue
        if equipment[0]['sg'] == 'n':
            if project_target[j]['SDSSg'] == 'y': continue
        if equipment[0]['sr'] == 'n':
            if project_target[j]['SDSSr'] == 'y': continue
        if equipment[0]['si'] == 'n':
            if project_target[j]['SDSSi'] == 'y': continue
        if equipment[0]['sz'] == 'n':
            if project_target[j]['SDSSz'] == 'y': continue
        # filter with equipment declination limit
        if float(equipment[0]['declination']) <= 0 and float(project_target[j]['lat']) < float(equipment[0]['declination']):
            continue
        if float(equipment[0]['declination']) > 0 and float(project_target[j]['lat']) > float(equipment[0]['declination']):
            continue

        target.append(int(project_target[j]['TID']))
    
    return target
'''
