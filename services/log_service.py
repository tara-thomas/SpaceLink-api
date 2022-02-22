import pymongo
from datetime import datetime
from services.target_service import time_deduction
from services.utils import *
import json
import csv

# client = pymongo.MongoClient("mongodb://localhost:27017/")
# db = client["SpaceLink"]
# observe_log = db['Observe_Log']
# schedule_col = db['Schedule']

def check_log_format(filename: str): 
    with open(filename, newline="") as csvfile:
        rows = csv.DictReader(csvfile)
        for index, row in enumerate(rows):
            # name check
            if len(row['Name']) == 0:
                return "rows "+ str(index+1) + " error : Please enter target name" 
            elif len(row['Name']) > 50 :
                return "rows "+ str(index+1) + " error : Name is too long"

            # check the value is digit or not,  
            for filter in FILTER:
                if row[filter + '_Exposure_Time'].isdigit() :
                    if int(row[filter + '_Exposure_Time']) < 0:
                        return "rows "+ str(index+1) + " error : \"" + filter + " Exposure Time\" format error"   
                else:
                    return "rows "+ str(index+1) + " error : " + filter + "Exposure Time format error. "      

                if row[filter + '_Images'].isdigit() :
                    if int(row[filter + '_Images']) < 0:
                        return "rows "+ str(index+1) + " error : \"" + filter + " Images\" format error"   
                else:
                    return "rows "+ str(index+1) + " error : " + filter + "Images format error. "      

    csvfile.close()
    return 1

def update_observe_time(filename : str, PID : int, usr: str):
    with open(filename, newline="") as csvfile:
        rows = csv.DictReader(csvfile)
    
        for index, row in enumerate(rows):

            # query by coordinate to check target exist or not
            query = "MATCH(t:target{name:$name}) return t.TID as TID"
            result = graph.run(query, name=row['Name']).data()

            TID = int(result[0]['TID']) 
                    
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
