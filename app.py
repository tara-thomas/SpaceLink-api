from flask import Flask, render_template, redirect, session, url_for, flash, request, jsonify
from flask_cors import CORS
from data.db_session import db_auth
#from services.accounts_service import create_user, login_user, get_profile, update_profile
from services.accounts_service import *
from services.project_service import *
from services.schedule_service import *
from services.friend_service import *
from services.target_service import *
from services.postgres_service import *
from services.log_service import *
import os, uuid, pathlib
import random

ALLOWED_EXTENSIONS = {'csv', 'tsv'}
UPLOAD_FOLDER = str(pathlib.Path().resolve())
app = Flask(__name__) #create application
app.secret_key = os.urandom(24) 
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

graph = db_auth() #connect to neo4j



@app.route('/', methods=['GET'])
def ind():
    return "It's working man"

'''
@app.route('/accounts/register', methods=['GET'])
def register_get():
    return render_template("accounts/register.html")
'''

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
        flash("Please populate all the registration fields"+country, "error")
        return {'username': username, 'name': name, 'email': email, 'affiliation': affiliation, 'title': title, 'country': country, 'password': password, 'confirm': confirm}

    # Check if password and confirm match
    if password != confirm:
        flash("Passwords do not match")
        return {'username': username, 'name': name, 'email': email, 'affiliation': affiliation, 'title': title, 'country': country, 'password': password, 'confirm': confirm}

    # Create the user
    user = create_user(username, name, email, affiliation, title, country, password)
    # Verify another user with the same email does not exist
    if not user:
        flash("A user with that email already exists.")
        return {'username': username, 'name': name, 'email': email, 'affiliation': affiliation, 'title': title, 'country': country, 'password': password, 'confirm': confirm}

    # return redirect(url_for("dashboard_get"))
    return "It worked!"

'''
@app.route('/accounts/login', methods=['GET'])
def login_get():
    # Check if the user is already logged in.  if yes, redirect to profile page.
    if "usr" in session:
        return {redirect(url_for("dashboard_get"))}
    else:
        return render_template("accounts/login.html")
'''


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

'''
@app.route('/accounts/map.html', methods=['GET'])
def map_get():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        return render_template("accounts/map.html")
    else:
        return redirect(url_for("login_get"))
'''

'''
@app.route('/accounts/map.html', methods=['POST'])
def map_post():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        return render_template("accounts/map.html")
    else:
        return redirect(url_for("login_get"))
'''

@app.route('/accounts/friends', methods=['GET'])
def viewFriends():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        friends = view_friend(usr)
        user_profile = get_profile(usr)
        return {'friends':friends, 'user_profile':user_profile}
        #return render_template("accounts/friends.html", friends=friends, user_profile=user_profile )
    else:
        return 'login'
        #return redirect(url_for("login_get"))

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

#created for ajax to join project for project on dashboard
@app.route('/joinProject', methods=['POST'])
def joinProject():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        PID = request.json['PID']
        auto_join(usr,int(PID))
        return {"Success": "Successfully joined the project."}
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/accounts/joinedProjects', methods=['GET'])
def getJoinedProjects():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        user_profile = get_profile(usr)
        projects = get_project_join(usr)
        if(projects == None):
            return "Not joined project yet!"
        return {'user_profile':user_profile,'projects':projects}
        #return render_template("accounts/joinedProjects.html", user_profile=user_profile, projects = projects)
    # else:
    #     return "login"
        #return redirect(url_for("login_get"))

@app.route('/accounts/manageprojects', methods=['GET'])
def manageProject():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        projects = user_manage_projects_get(usr)
        print(projects)
        return {'projects': projects}
        #return render_template("accounts/manageprojects.html", user_profile=user_profile, projects = projects)
    else:
        return "login"
        #return redirect(url_for("login_get"))

# 1019 for users to rank their joined projects
@app.route('/accounts/rankedProjects', methods=['GET'])
def getRankedProjects():

    EID = int(request.json['EID'])
    usr = request.headers['user']
              
    pid_list = get_equipment_project_priority(usr, EID)
    projects = get_project_info(pid_list); 
            
    return {'projects':projects}

# 0331 for users to rank their joined projects
@app.route('/accounts/rankedProjects', methods=['POST'])
def postRankedProjects():

    EID = int(request.json['EID'])
    usr = request.headers['user']
    user_profile = get_profile(usr)
        
    # only when user click the save button would update the database
    if request.json['method'] == 'save':
        pid_list = request.json['list']
        update_equipment_project_priority(usr,EID,pid_list)
        pid_list = get_equipment_project_priority(usr, EID)    
        projects = get_project_info(pid_list);             
        return {'projects':projects}

    if request.json['method'] == 'reset':
        projects = get_project_join(usr)
        projects = get_project_default_priority(projects)
        return {'projects':projects}

    if request.json['method'] == 'get':                
        pid_list = get_equipment_project_priority(usr, EID)
        projects = get_project_info(pid_list); 
        return {'projects':projects}

    return "login" 
        #return redirect(url_for("login_get"))

#created for ajax to get target for projects on dashboard
@app.route('/getTargetInfo', methods=['POST'])
def getTargetInfo():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        hid = request.json['PID']
        project_target = fliter_project_target(usr, int(hid))
        return jsonify(project_targets = project_target)
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/getTargetForProjectInfo', methods=['POST'])
def getTargetForProjectInfo():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        hid = request.json['PID'].strip()
        project_target = get_project_target(int(hid))
        return jsonify(project_targets = project_target)
    else:
        return "login"


@app.route('/getJoinedEquipmentInfo', methods=['POST'])
def getJoinedEquipmentInfo():
    hid = request.json['PID'].strip()
    project_equipments = get_project_equipment(int(hid))
    return jsonify(project_equipments = project_equipments)

@app.route('/equipment/schedule', methods=['POST'])
def getSchedule():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        uhaveid =  request.json['id']
        print("UHAVEID: ", uhaveid, "USER: ", usr)
        UID = get_uid(usr)
        EID = get_eid(uhaveid)
        return jsonify(query_schedule(UID,EID,str(date.today())))
        #return jsonify(generate_default_schedule(usr, uhaveid))
    else:
        return "login"

@app.route('/addfriend', methods=['POST'])
def addFriend():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        uid = request.json['UID'].strip()
        add_friend(usr, int(uid))
        return jsonify(success = "success")
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/getPMInfo', methods=['POST'])
def getPMInfo():
    hid = request.json['PID']
    project_manager = get_project_manager_name(int(hid))
    return jsonify(project_manager = project_manager)

@app.route('/accounts/profile', methods=['GET'])
def profile_get():
    # Make sure the user has an active session.  If not, redirect to the login page.
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        return {'user_profile':user_profile}
        #return render_template("accounts/profile.html", user_profile=user_profile)
    else:
        return "login"
        #return redirect(url_for("login_get"))


@app.route('/accounts/profile', methods=['POST'])
def profile_post():
    # Get the data from index.html
    username = request.json['username'].strip()
    name = request.json['name'].strip()
    affiliation = request.json['affiliation'].strip()
    title = request.json['title'].strip()
    country = request.json['country'].strip()
    # Make sure the user has an active session.  If not, redirect to the login page.
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = update_profile(usr, username, name, affiliation, title, country)
        user_profile = get_profile(usr)
        return {'user_profiel':user_profile}
        #return render_template("accounts/profile.html", user_profile=user_profile)
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/accounts/interests', methods=['GET'])
def viewInterest():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        interests = get_user_interest(usr)
        return {'user_profiel':user_profile, 'interests':interests}
        #return render_template("accounts/interests.html", user_profile=user_profile, interests=interests)
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/accounts/addInterest', methods=['POST'])
def addInterest():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        TID = request.json['TID']
        create_user_target(usr, int(TID))
        return jsonify(success = "Success")
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/accounts/deleteInterest', methods=['POST'])
def delInterest():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        TID = request.json['TID']
        delete_user_insterest(usr, int(TID))
        return jsonify(success = "Success")
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/accounts/createProject', methods=['GET'])
def createProj_get():
    # Make sure the user has an active session.  If not, redirect to the login page.
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        projects = get_project(usr)
        return {'user_profile':user_profile,'projects':projects}
        #return render_template("accounts/createProject.html", user_profile=user_profile, projects = projects)
    else:
        return "login"
        #return redirect(url_for("login_get"))


@app.route('/accounts/equipments', methods=['GET'])
def equipments_get():
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        user_profile = get_profile(usr)
        count = count_user_equipment(usr)
        if count == 0:
            flash("You don't have any equipment yet! Please add an equipment first", "error")
            return {'user_equipments':None}
            #return render_template("accounts/equipments.html", user_equipments = None)
        user_equipments = get_user_equipments(usr)
        return {'user_profile':user_profile,'user_equipments':user_equipments}
        #return render_template("accounts/equipments.html", user_profile=user_profile, user_equipments = user_equipments)
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/accounts/equipments', methods=['POST'])
def equipments_post():
    # user equipment parameter
    Site = request.json['site'].strip()
    Longitude = request.json['longitude'].strip()
    Latitude = request.json['latitude'].strip()
    Altitude = request.json['altitude'].strip()
    tz = request.json['time_zone'].strip()
    daylight = request.json['daylight_saving'].strip()
    wv = request.json['water_vapor'].strip()
    light_pollution = request.json['light_pollution'].strip()
    
    #equipments parameter
    aperture = request.json['aperture'].strip()
    Fov = request.json['fov'].strip()
    pixel_scale = request.json['pixel'].strip()
    tracking_accuracy = request.json['accuracy'].strip()
    lim_magnitude = request.json['mag'].strip()
    elevation_lim = request.json['deg'].strip()
    mount_type = request.json['mount_type'].strip()
    camera_type1 = request.json['camera_type1'].strip()
    camera_type2 = request.json['camera_type2'].strip()
    JohnsonB = request.json['JohnsonB'].strip()
    JohnsonV = request.json['JohnsonV'].strip()
    JohnsonR = request.json['JohnsonR'].strip()
    SDSSu = request.json['SDSSu'].strip()
    SDSSg = request.json['SDSSg'].strip()
    SDSSr = request.json['SDSSr'].strip()
    SDSSi = request.json['SDSSi'].strip()
    SDSSz = request.json['SDSSz'].strip()
    usr = request.headers['user']
    print(usr)
    session["usr"] = usr
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        # if request.form.get('button') == 'update':            
        #     hid = request.json['uhaveid'].strip() 
        #     print(hid)
        #     user_equipments = update_user_equipments(aperture,Fov,pixel_scale,tracking_accuracy,lim_magnitude,elevation_lim,mount_type,camera_type1,
        #     camera_type2,JohnsonB,JohnsonR,JohnsonV,SDSSu,SDSSg,SDSSr,SDSSi,SDSSz,
        #     usr,Site,Longitude,Latitude,Altitude,tz,daylight,wv,light_pollution,int(hid))
        equipments = create_equipments(aperture,Fov,pixel_scale,tracking_accuracy,lim_magnitude,elevation_lim,mount_type,camera_type1,camera_type2,JohnsonB,JohnsonR,JohnsonV,SDSSu,SDSSg,SDSSr,SDSSi,SDSSz)
        print(equipments.EID)
        user_equipments = create_user_equipments(usr,equipments.EID,Site,Longitude,Latitude,Altitude,tz,daylight,wv,light_pollution)
            # create spatial user equipment
            # postgres_create_user_equipments(int(user_equipments.id),get_uid(usr), equipments.EID,Longitude,Latitude,Altitude)
        # if request.form.get('button') == 'delete':            
        #     hid = request.json['uhaveid'].strip() 
        #     delete_user_equipment(usr,int(hid))
        #     # delete user's equipment in postgresSQL
        #     postgres_delete_user_equipments(int(hid))
        user_equipments = get_user_equipments(usr)
        return {'user_equipments':user_equipments}
        #return render_template("accounts/equipments.html", user_equipments = user_equipments)
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/projects/target', methods=['GET'])
def target_get():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        target = get_target()
        return {'target':target}
        #return render_template("projects/target.html", target = target)
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/projects/target', methods=['POST'])
def target_post():

    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        target = get_target()
        return {'target':target}
        #return render_template("projects/target.html", target = target)
    else:
        return "login"
        #return redirect(url_for("login_get"))

'''
@app.route('/projects/search', methods=['GET'])
def target_search_get():
    return render_template("projects/search_target.html")
'''

# 0703 change the function to query_from_simbad
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

    # text = '(?i).*'+text+'.*'
    # if request.form.get('button') == 'Search':
    # target = search_target(text)

    #return render_template("projects/search_target.html", target = target)
    return {'target': target}

@app.route('/projects/targetDetails', methods=['POST'])
def target_getDetails():
        name = request.json['targetName'].strip()
        target = get_targetDetails(name)
        return jsonify(targetDetails = target)


@app.route('/projects/project', methods=['GET'])
def project_get():

    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        projects = get_project(usr)
        return {'projects':projects}
        #return render_template("projects/project.html", projects = projects)
    else:
        return "login"
        #return redirect(url_for("login_get"))

@app.route('/projects/project', methods=['POST'])
def project_post():
    hid = request.form.get('PID').strip()
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        if request.form.get('button') == 'Detail':
            print(hid)
            project_target = get_project_target(int(hid))
            return {'project_target': project_target}
        elif request.form.get('button') == 'Create':
            return "project create"
            # return redirect(url_for("project_create_get"))
        elif request.form.get('button') == 'Apply_history':
            print('history')
            return "project apply history"
            # return redirect(url_for("project_apply_history_get"))
        elif request.form.get('button') == 'Join':
            PID = request.json['PID'].strip()
            flag = apply_project_status(usr,int(PID))
            if flag == 1:
                apply_project(usr,int(PID))
            #elif flag == 2:
                # handle already apply
            #elif flag == 3:
                #handle already join project
            #else:
                # handle error
        projects = get_project(usr)
        return {'projects': projects}
    else:
        return "login"
        # return redirect(url_for("login_get"))


@app.route('/projects/project_apply_history', methods=['GET'])
def project_apply_history_get():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        history = get_apply_history(usr)
        return {'history': history}
    else:
        return "login"
        # return redirect(url_for("login_get"))

@app.route('/projects/project_create', methods=['GET'])
def project_create_get():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        projects = user_manage_projects_get(usr)
        return {'projects': projects}
    else:
        return "login"
        # return redirect(url_for("login_get"))

@app.route('/accounts/createProject', methods=['POST'])
def project_create_post():    
    title = request.json['title'].strip()
    project_type = request.json['project_type'].strip()
    description = request.json['description'].strip()
    aperture_upper_limit = request.json['aperture_upper_limit']
    aperture_lower_limit = request.json['aperture_lower_limit']
    FoV_upper_limit = request.json['FoV_upper_limit']
    FoV_lower_limit = request.json['FoV_lower_limit']
    pixel_scale_upper_limit = request.json['pixel_scale_upper_limit']
    pixel_scale_lower_limit = request.json['pixel_scale_lower_limit']
    mount_type = request.json['mount_type'].strip()
    camera_type1 = request.json['camera_type1'].strip()
    camera_type2 = request.json['camera_type2'].strip()
    JohnsonB = request.json['JohnsonB'].strip()
    JohnsonV = request.json['JohnsonV'].strip()
    JohnsonR = request.json['JohnsonR'].strip()
    SDSSu = request.json['SDSSu'].strip()
    SDSSg = request.json['SDSSg'].strip()
    SDSSr = request.json['SDSSr'].strip()
    SDSSi = request.json['SDSSi'].strip()
    SDSSz = request.json['SDSSz'].strip()
    # PID = request.form.get('PID').strip()
    # PI = request.form.get('PI').strip()
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        #if request.form.get('button') == 'Create':
        print('create project')
        projects = create_project(usr,title,project_type,description,aperture_upper_limit,aperture_lower_limit,FoV_upper_limit,FoV_lower_limit,pixel_scale_upper_limit,pixel_scale_lower_limit,mount_type,camera_type1,camera_type2,JohnsonB,JohnsonR,JohnsonV,SDSSu,SDSSg,SDSSr,SDSSi,SDSSz)
        # if request.form.get('button') == 'Update':
        #     umanageid = request.form.get('umanageid').strip()
        #     projects = upadte_project(usr,int(PID),int(umanageid),title,project_type,description,aperture_upper_limit,aperture_lower_limit,FoV_upper_limit,FoV_lower_limit,pixel_scale_upper_limit,pixel_scale_lower_limit,mount_type,camera_type1,camera_type2,JohnsonB,JohnsonR,JohnsonV,SDSSu,SDSSg,SDSSr,SDSSi,SDSSz)
        # if request.form.get('button') == 'Delete':            
        #     umanageid = request.form.get('umanageid').strip()
        #     delete_project(usr,int(PID),int(umanageid))
        # projects = user_manage_projects_get(usr)
        return jsonify(projects = projects.PID)
    else:
        return "login"
        # return redirect(url_for("login_get"))

@app.route('/projects/createTarget', methods=['POST'])
def createTarget():
    targetName = request.json['name'].strip()
    ra = request.json['ra']
    dec = request.json['dec']
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        msg, tid = create_target(targetName, ra, dec)
        return jsonify(tid=tid)
    else:
        return "login"

@app.route('/projects/addTarget', methods=['POST'])
def addTarget():
    PID = request.json['PID']
    TID = request.json['TID']
    JohnsonB = request.json['JohnsonB'].strip()
    JohnsonV = request.json['JohnsonV'].strip()
    JohnsonR = request.json['JohnsonR'].strip()
    SDSSu = request.json['SDSSu'].strip()
    SDSSg = request.json['SDSSg'].strip()
    SDSSr = request.json['SDSSr'].strip()
    SDSSi = request.json['SDSSi'].strip()
    SDSSz = request.json['SDSSz'].strip()
    JohnsonBMin = request.json['JohnsonBMin'].strip()
    JohnsonVMin = request.json['JohnsonVMin'].strip()
    JohnsonRMin = request.json['JohnsonRMin'].strip()
    SDSSuMin = request.json['SDSSuMin'].strip()
    SDSSgMin = request.json['SDSSgMin'].strip()
    SDSSrMin = request.json['SDSSrMin'].strip()
    SDSSiMin = request.json['SDSSiMin'].strip()
    SDSSzMin = request.json['SDSSzMin'].strip()
    # TODO time to observe (array)
    time2observe = [JohnsonBMin, JohnsonRMin, JohnsonVMin, SDSSuMin, SDSSgMin, SDSSrMin, SDSSiMin, SDSSzMin]
    mode = request.json['mode'] # 0: general, 1: cycle
    if request.headers['user']:
        usr = request.headers['user']
        session["usr"] = usr
        target  = create_project_target(usr,int(PID),int(TID),JohnsonB, JohnsonR, JohnsonV, SDSSu, SDSSg, SDSSr, SDSSi, SDSSz, time2observe, int(mode))
        return jsonify(target = target)
    else:
        return "login"

# @app.route('/projects/project', methods=['POST'])
# def project_post():
#     hid = request.form.get('PID').strip()
#     if "usr" in session:
#         usr = session["usr"]
#         session["usr"] = usr
#         if request.form.get('button') == 'Detail':
#             print(hid)
#             project_target = get_project_target(int(hid))
#             return render_template("projects/project_target.html", project_target = project_target)
#     else:
#         return redirect(url_for("login_get"))


@app.route('/project/upload_target_from_file', methods=['POST'])
def upload_file():
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
            path = os.path.join(app.config['UPLOAD_FOLDER'],"upload_tmp")
            pathlib.Path(path).mkdir(parents=True,exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'],"upload_tmp",filename)
            file.save(filepath)
            
            #check the file format 
            check_format_result = check_format(filepath);
            if( check_format_result != "Success"):
                os.remove(filepath)
                return check_format_result
            #upload file to DB
            if(upload_2_DB(filepath,PID,usr)): 
                os.remove(filepath)
                return "Upload success"
            else:
                os.remove(filepath)
                return "Upload failed"

        else :
            print("Not supported file")


@app.route('/accounts/logout')
def logout():
    session.pop("usr", None)
    flash("You have successfully been logged out.", "info")
    return "login"
    # return redirect(url_for("login_get"))


if __name__ == '__main__':
    app.run(debug=True)