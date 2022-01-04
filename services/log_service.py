from data.db_session import db_auth
import pymongo
from datetime import datetime
from services.target_service import time_deduction
import json

graph = db_auth()

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
               
            # filter and mode check
            mode = int(row['Mode'])
            if mode < 0 or mode > 2 :
                return "rows "+ str(index+1) + " error : Mode format error"      
            
            for filter in FILTER:
                if row[filter].isdigit() :
                    if int(row[filter]) < 0 :
                        return "rows "+ str(index+1) + " error : \"" + filter + " Time\" format error"   
                else
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


def update_observe_time(filename : str, PID : int, usr: str):
         
      with open(filename, newline="") as csvfile:
        rows = csv.DictReader(csvfile)
        
        for index,row in rows:
    
            # query by coordinate to check target exist or not
            query = "MATCH(t:target{name:$nam}) return t.TID as TID"
    
            TID = int(result['TID']) 
            
            
            observeTime = []
            for filter in FILTER:
                observeTime.append(int(row[filter]))

            time_deduction(PID, TID, observe_time)


    return 1
    


# def query_log(user:str,date:str):
#     for result in observe_log.find({'user_email':user, 'date': {'$regex': date, '$options': 'i'}}):
#         print(result)



