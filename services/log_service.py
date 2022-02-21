from data.db_session import db_auth
import pymongo
from datetime import datetime
from services.target_service import time_deduction
import json
import csv

graph = db_auth()

ALLOWED_EXTENSIONS = {'csv', 'tsv'}
FILTER = ['lFilter','rFilter','gFilter','bFilter','haFilter','oiiiFilter','siiFilter','duoFilter','multispectraFilter', \
            'JohnsonU','JohnsonB','JohnsonV','JohnsonR','JohnsonI',\
            'SDSSu','SDSSg','SDSSr','SDSSi','SDSSz']
# client = pymongo.MongoClient("mongodb://localhost:27017/")
# db = client["SpaceLink"]
# observe_log = db['Observe_Log']
# schedule_col = db['Schedule']

# def upload_log(log:dict):
#     observe_log.insert(log)
#     for i in log["log"]:
#         query1 = "match x=(p:project{PID:$pid})-[r:PHaveT]->(t:target{TID:$tid}) set r.Time_to_Observe={ramain:$remain} return r.Time_to_Observe" #update new time_to_observe
#         query2 = "match x=(p:project{PID:$pid})-[r:PHaveT]->(t:target{TID:$tid}) return r.Time_to_Observe"  #query old time_to_observe
#         dateformat = '%Y-%m-%d %H:%M:%S.%f'
#         start = datetime.strptime(i['start_time'],dateformat)
#         end = datetime.strptime(i['end_time'],dateformat)

#         delta = end - start 
#         observe_time = delta.seconds//60

#         print("tid ", i['tid'], ", start time:", i['start_time'], ", end_time: ",i['end_time'])
#         print("observe_time: ",delta, ",  ",observe_time)
#         #TODO : here can optimize by preftching next item 
#         remain_time = graph.run(query2,pid = int(i['pid']),tid = int(i['tid'])).data()
#         remain_time[i['fliter_type']] = remain_time[i['fliter_type']] - observe_time
#         graph.run(query1, pid = int(i['pid']),tid = int(i['tid']), remain = remain_time)

def check_log_format(filename: str): 
    with open(filename, newline="") as csvfile:
        rows = csv.DictReader(csvfile)

        for index, row in enumerate(rows):
            # name check
            if len(row['Name']) == 0:
                return "rows "+ str(index+1) + " error : Please enter target name" 
            elif len(row['Name']) > 50 :
                return "rows "+ str(index+1) + " error : Name is too long"

            # check date
               
            # # filter and mode check
            # mode = int(row['Mode'])
            # if mode < 0 or mode > 2 :
            #     return "rows "+ str(index+1) + " error : Mode format error"      
            
            # filter + time , filter + 
            for filter in FILTER:
                if row[filter + '_Exposure_Time'].isdigit() :
                    if int(row[filter + ' Exposure Time']) < 0:
                        return "rows "+ str(index+1) + " error : \"" + filter + " Exposure Time\" format error"   
                else:
                    return "rows "+ str(index+1) + " error : " + filter + "Exposure Time format error. "      

                if row[filter + '_Images'].isdigit() :
                    if int(row[filter]) < 0:
                        return "rows "+ str(index+1) + " error : \"" + filter + " Images\" format error"   
                else:
                    return "rows "+ str(index+1) + " error : " + filter + "Images format error. "      

            # if mode:
            #     try:
            #         time = float(row['Total_cycle__time'])
            #         if time < 0:
            #             raise Exception
            #     except ValueError:
            #         return "rows "+ str(index+1) + " error : \"Total cycle time\" format error"   
    csvfile.close()
    return "Success"

def update_observe_time(filename : str, PID : int, usr: str):
    with open(filename, newline="") as csvfile:
        rows = csv.DictReader(csvfile)
    
    for index, row in rows:

        # query by coordinate to check target exist or not
        query = "MATCH(t:target{name:$name}) return t.TID as TID"
        result = graph.run(query, name=usr).data()

        TID = int(result['TID']) 
                
        observeTime = []
        for filter in FILTER:
            exposure = int(row[filter + '_Exposure_Time'])
            images = int(row[filter + '_Images'])   
            observeTime.append(exposure * images)

        time_deduction(PID, TID, observeTime)

    return 

def allowed_file(filename: str):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# def query_log(user:str,date:str):
#     for result in observe_log.find({'user_email':user, 'date': {'$regex': date, '$options': 'i'}}):
#         print(result)
