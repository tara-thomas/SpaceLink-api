from os import scandir
from data.db_session import db_auth
from typing import Optional
from passlib.handlers.sha2_crypt import sha512_crypt as crypto
from services.classes import User, Target, Equipments, Project, Schedule
from datetime import datetime, timedelta, date
from services.project_service import get_project_target
from services.accounts_service import get_uid
from flask import jsonify

import astro.declination_limit_of_location as declination
import astro.astroplan_calculations as obtime
import random
import pymongo

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from string import Template

import smtplib

graph = db_auth()
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["SpaceLink"]
schedule_db = db['schedule']

# needs modification
'''
#create a new schedule for a equipment
def create_schedule(eid: int, uhaveid: int):
    # get EID
    # EID = get_eid(uhaveid)

    count = graph.run("MATCH (s:schedule) return s.SID order by s.SID DESC limit 1").data()
    schedule = Schedule()
    if len(count) == 0:
        schedule.SID = 0
    else:
        schedule.SID = count[0]['s.SID']+1
    
    # schedule.date #Y:M:D

    # get nighttime
    observe_section, current_time = get_night_time(uhaveid)

    schedule.observe_section = observe_section
    schedule.last_update = str(current_time)
    graph.create(schedule)
    print(eid)
    query="MATCH (e:equipments {EID: $EID}) MATCH (s:schedule {SID: $SID}) CREATE (e)-[r:EhaveS {ehavesid:$ehavesid}]->(s)"
    count = graph.run("MATCH ()-[r:EhaveS]->() return r.ehavesid  order by r.ehavesid DESC limit 1").data()
    if len(count) == 0:
        cnt = 0
    else:
        cnt = count[0]['r.ehavesid']+1

    graph.run(query, EID=eid, SID=schedule.SID, ehavesid=cnt)

    return schedule.SID

#load a equipmeent's schedule
def load_schedule(uhaveid: int):
    # find the equipment
    EID = get_eid(uhaveid)

    # if the equipment doesn't have a schedule, create one!
    query_count_schedule = "MATCH (e:equipments{EID:$EID})-[r:EhaveS]->(s:schedule) RETURN count(r) as cnt"
    result_count = graph.run(query_count_schedule, EID=EID).data()
    if result_count[0]['cnt'] == 0:
        SID = create_schedule(EID, uhaveid)
    else:
        query_sid = "match (e:equipments{EID:$EID})-[r:EhaveS]->(s:schedule) return s.SID as SID"
        sid = graph.run(query_sid, EID=EID).data()
        SID = sid[0]['SID']

    # get nighttime
    new_observe_section, current_time = get_night_time(uhaveid)

    # find the schedule
    query_schedule = "MATCH (e:equipments{EID:$EID})-[r:EhaveS]->(s:schedule) return s.observe_section as observe_section, s.last_update as last_update"
    result = graph.run(query_schedule, EID=EID).data()
    old_observe_section = result[0]['observe_section']
    previous_time = result[0]['last_update']

    # calculate the updated schedule
    updated_schedule = [-1]*24
    format = '%Y-%m-%d %H:%M:%S'
    gap = current_time - datetime.strptime(previous_time, format)
    if len(str(gap)) > 10:
        updated_schedule = new_observe_section
    else:
        start_index = int(str(gap).split(":")[0])
        j = start_index
        for i in range(24):
            if j < 24:
                updated_schedule[i] = old_observe_section[j]
                j+=1
            else:
                updated_schedule[i] = new_observe_section[i]

    # return the new calculated schedule to front-end
    return updated_schedule, str(current_time), SID

#this function save the schedule 
def save_schedule(SID: int, last_update: str, observe_section: list):
    query_save_schedule = "match (s:schedule{SID:$SID}) set s.last_update=$last_update, s.observe_section=$observe_section"

    graph.run(query_save_schedule, SID=SID, last_update=last_update, observe_section=observe_section)
'''


# 0331 generate default schedule by sorting target
def generate_default_schedule(usr: str, uhaveid: int):
    eid = get_eid(uhaveid)
    query = "MATCH (e:equipments {EID:$eid}) return e.project_priority as project_priority"
    result = graph.run(query, eid=eid).data()
    # pid_list = [13,4,1]
    pid_list = result[0]['project_priority']

    if not pid_list:
        print("No joined projects.")
        return

    # 0526
    # arrange the schedule until it is full
    schedule_target, schedule_pid = [], []
    for pid in pid_list:
        project_target = get_project_target(pid)
        # print("PROJECT TARGET: ", project_target)
        # print("\n\n\n\n\n\n\n\n\n")
        sorted_target = sort_project_target(project_target)
        # print("SORTED TARGET: ", sorted_target)
        # print("\n\n\n\n\n\n\n\n\n")
        schedule_target += sorted_target
        schedule_pid += [pid] * len(sorted_target)
        # print("SCHEDULE TARGET: ", schedule_target)
        # print("\n\n\n\n\n\n\n\n\n")
        if (len(schedule_target) > 100):
            break

    print(len(schedule_target))
    # print("\nSCHEDULE TARGET:\n", schedule_target)
    default_schedule, target_datetime = get_observable_time(uhaveid, schedule_pid, schedule_target)

    schedule = {}
    schedule["default_schedule"] = default_schedule
    schedule["target_schedule"] = target_datetime
    # print(default_schedule)
    # print(target_datetime)
    uid = get_uid(usr)

    # 0107 temporally comment this
    # save_schedule(uid,eid,schedule)

    return [default_schedule, target_datetime]

# 0331 sort targets' priority
def sort_project_target(project_target):
    # sort algorithm (remember to filter out the target that t2o = 0)
    '''TODO'''

    # shuffle for now
    random.shuffle(project_target)
    return project_target

# get the equipment id
def get_eid(uhaveid):
    query_eid = "MATCH (x:user)-[h:UhaveE{uhaveid:$uhaveid}]->(e:equipments) return e.EID as EID"
    eid = graph.run(query_eid, uhaveid=uhaveid).data()

    eid = int(eid[0]['EID'])

    return eid

# 0505 get the time need to observe of each target in projects
def get_time2observe(pid, tid):
    query = "MATCH (p:project{PID:$pid})-[r:PHaveT]->(t:target{TID:$tid}) RETURN r.Time_to_Observe as T2O, r.Mode as mode"
    result = graph.run(query, pid=pid, tid=tid).data()

    t2o = result[0]['T2O']
    # t2o = [1000, 1000, 1080, 0, 300, 0, 0, 1500]
    mode = result[0]['mode']
    # mode = 0
    # cycle_time = result[0]['cycle_time']
    # cycle_time = [-1, -1, -1, -1, -1, -1, -1, -1]

    return t2o, mode

# 0421 + 0505 + 0512
def get_observable_time(uhaveid: int, schedule_pid: list, sorted_target: list):
    current_time = datetime.now()
    observability = []
    target_datetime = []
    tid_list = []
    # 0602
    schedule_filled = [-1]*1440

    # get information from uhavee and equipment table
    query_relation = "MATCH (x:user)-[h:UhaveE{uhaveid:$uhaveid}]->(e:equipments) return h.longitude as longitude, h.latitude as latitude, h.altitude as altitude, h.time_zone as time_zone, e.deg as deg"
    eq_info = graph.run(query_relation, uhaveid=uhaveid).data()
    longitude = float(eq_info[0]['longitude'])
    latitude = float(eq_info[0]['latitude'])
    altitude = float(eq_info[0]['altitude'])
    time_zone = eq_info[0]['time_zone']
    deg = float(eq_info[0]['deg'])

    # 0512
    filter_array = ["Johnson_B", "Johnson_V", "Johnson_R", "SDSS_u", "SDSS_g", "SDSS_r", "SDSS_i", "SDSS_z"]
    hint_msgs = {}
    # /0512

    # 1020 convert basetime from local to UTC time
    base_time = datetime.strptime(str(current_time).split(' ')[0]+' 12:00', '%Y-%m-%d %H:%M')
    base_time -= timedelta(hours=time_zone)
    utc2local = False
    # /1020
    for pid, tar in zip(schedule_pid, sorted_target):
        tid = int(tar['TID'])
        ra = float(tar['lon'])
        dec = float(tar['lat'])

        # get the time still need to observe of this target (an array of time by filters)
        t2o, mode = get_time2observe(pid, tid)

        # 0512
        hint = "Please Observe with Filter"
        t2o_total = 0
        for i in range(len(filter_array)):
            if t2o[i] != 0:
                t2o_total += t2o[i]
                hint += (" " + filter_array[i] + ",")
        
        hint = hint[:len(hint)-1]
        if mode != 0:
            hint += (", and " + str(mode) + " seconds for each filter")
        hint += '.'
        hint_msgs[str(tid)] = hint
        # /0512

        # get the observable time
        t_start, t_end = obtime.run(uhaveid, longitude, latitude, altitude, deg, tid, ra, dec, base_time)
        # print(uhaveid, longitude, latitude, altitude, deg, tid, ra, dec)
        # print(t_start, t_end)

        # make the observability chart to each target
        if str(t_start) != 'nan' and str(t_end) != 'nan':
            t_start = datetime.strptime(str(t_start)[:16], '%Y-%m-%dT%H:%M')
            t_end = datetime.strptime(str(t_end)[:16], '%Y-%m-%dT%H:%M')
            # 1020 convert back to LOCAL time
            t_start += timedelta(hours=time_zone)
            t_end += timedelta(hours=time_zone)
            if not utc2local:
                base_time += timedelta(hours=time_zone)
                utc2local = True
            # /1020

            tid_list.append(tid)

            # offset from base time to target rise time 
            if t_start > base_time:
                t_offset = t_start-base_time
            else:
                t_offset = 0
            
            # how long can the target observation could last
            t_last = t_end-t_start
            # if the target doesn't need to be observed thant long
            if timedelta(minutes=t2o_total) < t_last:
                t_last = timedelta(minutes=t2o_total)

            # 0602
            temp = [-1]*1440
            if t_offset != 0:
                t_offset = t_offset.seconds//60
            else:
                t_offset = 0
            t_last = t_last.seconds//60

            # set observable minute of each target in the array to its TID
            temp[t_offset:t_offset+t_last+1] = [tid] * (t_last+1)
            temp = temp[:1440]

            # check if the schedule is full
            schedule_filled[t_offset:t_offset+t_last+1] = [tid] * (t_last+1)
            schedule_filled = schedule_filled[:1440]

            observability.append(temp.copy())

            # 0921 add datetime format to each observable target
            temp = {}
            temp['TID'] = tid
            temp['Start'] = t_start
            temp['End'] = t_start + timedelta(minutes=t_last)
            temp['Hint'] = hint
            target_datetime.append(temp.copy())
            
            # if the schedule is full, stop calculation
            if -1 not in schedule_filled:
                # print("FILLED by " + str(i+1) + " targets.")
                break

    # calculate default schedule
    default_schedule, default_schedule_chart, targets_observable_time = calculate_default_schedule(base_time, tid_list, observability, hint_msgs)

    '''
    default_schedule: TID, start / end time in datetime format, HINT
    default_schedule_chart: array len 1440, TID in each element
    targets_observable_time: array len 1440 for each target (-1 or TID in each element)
    '''

    # return default_schedule, default_schedule_chart, targets_observable_time, observability_datetime
    return default_schedule, target_datetime

# 0505 + 0512
def calculate_default_schedule(base_time, tid_list, observable_time, hint_msgs):
    default_schedule = []
    default_schedule_chart = [-1]*1440

    last_tid = -1
    tid_schedule = []
    divide_time = []
    # 0602
    til_last_min = False

    # put targets into default schedule
    for i in range(1440):
        for j in range(len(tid_list)):
            if observable_time[j][i] != -1:
                default_schedule_chart[i] = observable_time[j][i]
                break
        # calculate the time between two targets
        if default_schedule_chart[i] != last_tid:
            delta = timedelta(minutes=i)
            # print(base_time+delta)
            tid_schedule.append(last_tid)
            divide_time.append(base_time+delta)
        last_tid = default_schedule_chart[i]
        # 0602 consider the target to the end of the list
        if i == 1439 and default_schedule_chart[i] != -1:
            til_last_min = True
            delta = timedelta(minutes=i)
            tid_schedule.append(default_schedule_chart[i])
            divide_time.append(base_time+delta)

    for i in range(len(tid_schedule)):
        temp = {}
        # 0602 modify
        if i == len(tid_schedule)-1 and til_last_min:
            temp['TID'] = tid_schedule[i]
            temp['Start'] = divide_time[i-1]
            temp['End'] = divide_time[i]+timedelta(minutes=1)
            temp['Hint'] = hint_msgs[str(tid_schedule[i])]
            default_schedule.append((temp.copy()))
        elif tid_schedule[i] != -1:
            temp['TID'] = tid_schedule[i]
            temp['Start'] = divide_time[i-1]
            temp['End'] = divide_time[i]-timedelta(minutes=1)
            temp['Hint'] = hint_msgs[str(tid_schedule[i])]
            default_schedule.append((temp.copy()))

    return default_schedule, default_schedule_chart, observable_time

def save_schedule(UID: int, EID: int, schedule: list):
    data = {}
    data['UID'] = UID
    data['EID'] = EID
    data['date'] = str(date.today())
    data['schedule'] = schedule
    print(data)
    schedule_db.insert_one(data)

def query_schedule(UID: int, EID: int, date: str):
    print(date)
    result = schedule_db.find_one({'UID': UID, 'EID': EID, 'date': date})
    # print(jsonify(result["schedule"]))
    return result['schedule']['default_schedule'], result['schedule']['target_schedule']


