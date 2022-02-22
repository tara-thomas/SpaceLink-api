from flask import Flask, render_template, redirect, session, url_for, flash, request, jsonify
from flask_cors import CORS
from services.account_service import *
from services.project_service import *
from services.schedule_service import *
# from services.friend_service import *
from services.target_service import *
from services.log_service import *
from services.utils import *
from werkzeug.utils import secure_filename
import os, uuid, pathlib
import random
import numpy as np

UPLOAD_FOLDER = str(pathlib.Path().resolve())
app = Flask(__name__) #create application
app.secret_key = os.urandom(24) 
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)


@app.route('/', methods=['GET'])
def ind():
    return "It's working man"

@app.route('/test/test', methods=['GET'])
def test():
    return "It's a test"

# Y
@app.route('/accounts/register', methods=['POST'])
def register_post():
    # Get the form data from register.html
    print(request.json)
    username = request.json['username'].strip()
    name = request.json['name']
    email = request.json['email'].lower().strip()
    affiliation = request.json['affiliation'].strip()
    title = request.json['title'].strip()
    country = request.json['country'].strip()
    password = request.json['password'].strip()
    confirm = request.json['confirm'].strip()

    # Check for blank fields in the registration form
    if not username or not name or not email or not affiliation or not title  or not country or not password or not confirm:
        return "Please populate all the registration fields"+country, 400
        #return {'username': username, 'name': name, 'email': email, 'affiliation': affiliation, 'title': title, 'country': country, 'password': password, 'confirm': confirm}

    # Check if password and confirm match
    if password != confirm:
        return "Passwords do not match", 400
        # return {'username': username, 'name': name, 'email': email, 'affiliation': affiliation, 'title': title, 'country': country, 'password': password, 'confirm': confirm}

    # Create the user
    user = create_user(username, name, email, affiliation, title, country, password)
    # Verify another user with the same email does not exist
    if not user:
        return "A user with that email already exists.", 400
        # return {'username': username, 'name': name, 'email': email, 'affiliation': affiliation, 'title': title, 'country': country, 'password': password, 'confirm': confirm}
        
    return "It worked!", 200

'''
# N
@app.route('/accounts/login', methods=['GET'])
def login_get():
    # Check if the user is already logged in.  if yes, redirect to profile page.
    if "usr" in session:
        return {redirect(url_for("dashboard_get"))}
    else:
        return render_template("accounts/login.html")
'''

# Y
@app.route('/accounts/login', methods=['POST'])
def login_post():
    # Get the form data from login.html
    email = request.json['email']
    password = request.json['password']
    if not email or not password:
        return "Record not found", 400

    # Validate the user
    user = login_user(email, password)
    if not user:
        return "No account for that email address or the password is incorrect", 401

    # Log in user and create a user session, redirect to user profile page.
    usr = request.json["email"]
    session["usr"] = usr
    return usr

# Y
@app.route('/accounts/index', methods=['GET'])
def dashboard_get():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        user_profile = get_profile(usr)
        projects = get_project(usr)
        return {'user_profile': user_profile, 'projects': projects}
    else:
        return "login"

# Y
@app.route('/searchProject', methods=['POST'])
def searchProject():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        # if search button clicked
        if request.json['method'] == 'search':
            text = request.json['list'].strip()
            searched_projects = search_project(text)
            return {'searched_projects': searched_projects}
        if request.json['method'] == 'select':
            PID = request.json['PID']
            project = get_project_detail(PID)
            join_status = get_join_status(usr, PID)
            return {'project': project, 'join_status': join_status}
    else:
        return "login"

# Y
@app.route('/getQualifiedEquipment', methods=['POST'])
def getQualifiedEquipment():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        PID = request.json['PID']
        qualified_equipment_list = get_qualified_equipment(usr, int(PID))
        return {'qualified_equipment_list': qualified_equipment_list}
    else:
        return "login"

# Y created for ajax to join project for project on dashboard
@app.route('/joinProject', methods=['POST'])
def joinProject():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        PID = request.json['PID']
        # get the equipment user selected
        # selected_equipment = request.json['selected_equipment']
        selected_eid, selected_equipment = get_qualified_equipment(usr, PID)
        auto_join(usr, int(PID), selected_eid)
        return {"Success": "Successfully joined the project."}
    else:
        return "login"

# N!
@app.route('/accounts/joinedProjects', methods=['GET'])
def getJoinedProjects():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        user_profile = get_profile(usr)
        projects = get_project_join(usr)
        print(projects)
        if(projects == None):
            return "Not joined project yet!"
        return {'user_profile': user_profile,'projects': projects}
    else:
        return "login"

# Y
@app.route('/accounts/manageprojects', methods=['GET'])
def manageProject():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        projects = user_manage_projects_get(usr)

        return {'projects': projects}
    else:
        return "login"

# N? for users to rank their joined projects
@app.route('/accounts/rankedProjects', methods=['GET'])
def getRankedProjects():
    EID = int(request.json['EID'])
    usr = request.headers['user']
              
    pid_list = get_equipment_project_priority(usr, EID)
    projects = get_project_info(pid_list)
            
    return {'projects': projects}

# Y for users to rank their joined projects
@app.route('/accounts/rankedProjects', methods=['POST'])
def postRankedProjects():
    EID = int(request.json['EID'])
    usr = request.headers['user']
        
    # only when user click the save button would update the database
    if request.json['method'] == 'save':
        pid_list = request.json['list']
        update_equipment_project_priority(usr, EID, pid_list)
        pid_list = get_equipment_project_priority(usr, EID)    
        projects = get_project_info(pid_list)
        return {'projects': projects}

    if request.json['method'] == 'reset':
        projects = get_project_join(usr)
        projects = get_project_default_priority(projects)
        return {'projects': projects}

    if request.json['method'] == 'get':                
        pid_list = get_equipment_project_priority(usr, EID)
        projects = get_project_info(pid_list); 
        return {'projects': projects}

    return "login" 

# Y created for ajax to get target for projects on dashboard
@app.route('/getTargetInfo', methods=['POST'])
def getTargetInfo():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        hid = request.json['PID']
        # project_target = fliter_project_target(usr, int(hid))
        project_target = get_project_target(int(hid))
        return jsonify(project_targets=project_target)
    else:
        return "login"

# Y
@app.route('/getTargetForProjectInfo', methods=['POST'])
def getTargetForProjectInfo():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        hid = request.json['PID']
        _, project_target = get_progress_percentage(int(hid))
        return jsonify(project_targets=project_target)
    else:
        return "login"

# Y
@app.route('/getJoinedEquipmentInfo', methods=['POST'])
def getJoinedEquipmentInfo():
    pid = request.json['PID']
    project_equipments = get_project_equipment(pid)
    return jsonify(project_equipments = project_equipments)

# Y
@app.route('/equipment/schedule', methods=['POST'])
def getSchedule():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        uhaveid =  request.json['id']
        UID = get_uid(usr)
        EID = get_eid(uhaveid)
        # return jsonify(query_schedule(UID, EID, str(date.today())))
        return jsonify(generate_default_schedule(usr, uhaveid))
    else:
        return "login"

# Y
@app.route('/getPMInfo', methods=['POST'])
def getPMInfo():
    hid = request.json['PID']
    project_manager = get_project_manager_name(int(hid))
    return jsonify(project_manager = project_manager)

@app.route('/accounts/profile', methods=['GET'])
def profile_get():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        return {'user_profile': user_profile}
    else:
        return "login"

@app.route('/accounts/profile', methods=['POST'])
def profile_post():
    username = request.json['username'].strip()
    name = request.json['name'].strip()
    affiliation = request.json['affiliation'].strip()
    title = request.json['title'].strip()
    country = request.json['country'].strip()

    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = update_profile(usr, username, name, affiliation, title, country)
        user_profile = get_profile(usr)
        return {'user_profiel':user_profile}
    else:
        return "login"

# Y
@app.route('/accounts/equipments', methods=['GET'])
def equipments_get():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        user_profile = get_profile(usr)
        count = count_user_equipment(usr)
        if count == 0:
            flash("You don't have any equipment yet! Please add an equipment first", "error")
            return {'user_equipments': None}
        user_equipments = get_user_equipments(usr)
        return {'user_profile': user_profile,'user_equipments': user_equipments}
    else:
        return "login"

# Y new equipment attributes
@app.route('/accounts/equipments', methods=['POST'])
def equipments_post():
    # equipment specs
    if (request.json['method'] == 'update' or request.json['method'] == 'create') :
        telName = request.json['telName'].strip()
        focalLength = int(request.json['focalLength'])
        diameter = int(request.json['diameter'])

        # camera specs
        camName = request.json['camName'].strip()
        pixelSize = int(request.json['pixelSize'])
        sensorW = int(request.json['sensorW'])
        sensorH = int(request.json['sensorH'])
        camera_type1  = request.json['camera_type1'].strip()
        camera_type2 = request.json['camera_type2'].strip()

        # filters
        if request.json['method'] == 'create':
            filterArray = []
            for filter in FILTER:
                filterArray.append(request.json[filter])
        
        if request.json['method'] == 'update':
            filterArray = request.json['filterArray']

        # mount
        mountName = request.json['mountName'].strip()
        mount_type = request.json['mount_type'].strip()
        deg = request.json['deg']

        # barlow / focal reducer
        barlowName = request.json['barlowName'].strip()
        magnification = int(request.json['magnification'])

        # calculated specs (need to save focalRatio, fovDeg, and resolution)
        focalRatio = focalLength * magnification / diameter
        sensorSize = pixelSize * sensorW / 1000
        fovRad = np.arctan(sensorSize / (focalLength * magnification))
        fovDeg = fovRad * 360 / (2 * np.pi)
        fovArcsec = fovDeg * 3600
        resolution = fovArcsec / sensorW

        # user-equipment parameter
        site = request.json['site'].strip()
        longitude = request.json['longitude']
        latitude = request.json['latitude']
        altitude = request.json['altitude']
        tz = request.json['time_zone']
        sq = request.json['sky_quality']

    usr = request.headers['user']
    session["usr"] = usr
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr

        if request.json['method'] == 'delete':            
            hid = request.json['uhaveid']
            delete_user_equipment(usr, int(hid))

        if request.json['method'] == 'update':            
            hid = request.json['uhaveid'] 
            print(hid)
            user_equipments = update_user_equipments(telName, focalLength, diameter, camName, pixelSize, sensorW, sensorH, camera_type1, camera_type2, filterArray,
                                                    mountName, mount_type, deg, barlowName, magnification, usr, hid, site, longitude, latitude, altitude, tz, sq)

        if request.json['method'] == 'create':  
            equipments = create_equipments(telName, focalLength, diameter, camName, pixelSize, sensorW, sensorH, camera_type1, camera_type2, filterArray,
                                        mountName, mount_type, deg, barlowName, magnification, focalRatio, fovDeg, resolution)
            user_equipments = create_user_equipments(usr, equipments.EID, site, longitude, latitude, altitude, tz, sq)
        
        user_equipments = get_user_equipments(usr)
        return {'user_equipments':user_equipments}
    else:
        return "login"

# Y change the function to query_from_simbad
@app.route('/projects/search', methods=['POST'])
def target_search_post():
    if 'search' in request.json:
        text = request.json['search'].strip()
        target = query_simbad_byName(text)
    else:
        coord = request.json['searchCoord'].strip()
        rad = request.json['rad'].strip()
        unit = request.json['unit'].strip()
        target = query_simbad_byCoord(coord, float(rad), unit)
    
    return {'target': target}

# Y
@app.route('/accounts/createProject', methods=['POST'])
def project_create_post():
    # project attributes
    project_type = request.json['project_type'].strip()
    title = request.json['title'].strip()
    description = request.json['description'].strip()
    FoV_lower_limit = request.json['FoV_lower_limit']
    resolution_upper_limit = request.json['resolution_upper_limit']

    # required camera type
    required_camera_type = request.json['camera_type1']

    # required filters
    required_filter = []
    for filter in FILTER:
        required_filter.append(request.json[filter])
    
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        if request.json['method'] == 'create':
            print('create project')
            projects = create_project(usr, project_type, title, description, FoV_lower_limit, resolution_upper_limit, required_camera_type, required_filter)
        if request.json['method'] == 'update':
            print('update project')
            umanageid = request.json['umanageid']
            PID = request.json['PID']
            projects = update_project(usr, int(PID), int(umanageid), project_type, title, description, FoV_lower_limit, resolution_upper_limit, required_camera_type, required_filter)
            return "updated"
        if request.json['method'] == 'delete':            
            umanageid = request.json['umanageid']
            PID = request.json['PID']
            delete_project(usr, int(PID), int(umanageid))
            return "deleted"

        return jsonify(projects=projects.PID)
    else:
        return "login"

# Y
@app.route('/projects/createTarget', methods=['POST'])
def createTarget():
    targetName = request.json['name'].strip()
    ra = request.json['ra']
    dec = request.json['dec']
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        msg, tid = create_target(targetName, ra, dec)
        return jsonify(tid=tid), 201
    else:
        return "login", 400

# Y
@app.route('/projects/addTarget', methods=['POST'])
def addTarget():
    PID = request.json['PID']
    TID = request.json['TID']
    # all filters
    filter2observe, time2observe = [], []
    for filter in FILTER:
        filter2observe.append(request.json[filter])
        time2observe.append(int(request.json[filter.replace("Filter", "")+"Min"]) if request.json[filter] else 0)
    mode = request.json['mode'] # 0: staring, 1: cycle

    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        if request.json['method'] == 'create':
            target  = create_project_target(usr, int(PID), int(TID), filter2observe, time2observe, int(mode))
            return jsonify(target = target), 201
        if request.json['method'] == 'update':
            target  = update_project_target(int(PID), int(TID), filter2observe, time2observe, int(mode))
            return jsonify(target = target), 201
        if request.json['method'] == 'delete':
            delete_project_target(int(PID), int(TID))
            return "deleted", 201
    else:
        return "Error", 500

@app.route('/projects/deleteProjectTarget', methods=['POST'])
def deleteProjectTarget():
    PID = request.json['PID']
    TID = request.json['TID']

    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr        
        delete_project_target(int(PID), int(TID))
        return "deleted", 201
    else:
        return "login", 400

@app.route('/project/uploadTarget', methods=['POST'])
def upload_target():
    usr = session["usr"]
    session["usr"] = usr
    PID = request.json['PID'].strip()
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            print("file not found")
            return "Upload failed"
        file = request.files['file']
        # If the user does not select a file, the response submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return "Upload failed"
        if file and allowed_file(file.filename):
            #certe random and secure name forthe upload file 
            filename = secure_filename(file.filename) + '_' +str(uuid.uuid4())
            print(filename)

            #if the directory not exist, then create one 
            path = os.path.join(app.config['UPLOAD_FOLDER'],"upload_tmp")
            pathlib.Path(path).mkdir(parents=True,exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'],"upload_tmp",filename)
            file.save(filepath)
            
            #check the file format 
            check_format_result = check_format(filepath)
            if( check_format_result != "Success"):
                os.remove(filepath)
                return 0
            #upload file to DB
            tar_list = upload_2_DB(filepath,PID,usr)
            os.remove(filepath)
            
            return tar_list
            
        else:
            print("Not supported file")

@app.route('/project/uploadLog', methods=['POST'])
def upload_log():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
    else:
        return "Authentication Failed."
    print (request.json)
    PID = request.json['PID'].strip()
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            print("file not found")
            return "Upload failed"
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return "Upload failed"
        if file and allowed_file(file.filename):
            #certe random and secure name forthe upload file 
            filename = secure_filename(file.filename) + '_' +str(uuid.uuid4())
            print(filename)

            #if the directory not exist, then create one 
            path = os.path.join(app.config['UPLOAD_FOLDER'],"log_tmp")
            pathlib.Path(path).mkdir(parents=True,exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'],"log_tmp",filename)
            file.save(filepath)
            
            #check the file format 
            check_format_result = check_log_format(filepath)
            if( check_format_result != 1):
                os.remove(filepath)
                return 0
            #update the observe time
            if(update_observe_time(filepath,PID,usr)): 
                os.remove(filepath)
                return 1
            else:
                os.remove(filepath)
                return 0

        else :
            print("The file format is not supported\n")


@app.route('/accounts/logout')
def logout():
    session.pop("usr", None)
    flash("You have successfully been logged out.", "info")
    
    return "login"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
