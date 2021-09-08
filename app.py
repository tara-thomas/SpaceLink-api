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
import os
import random

app = Flask(__name__) #create application
app.secret_key = os.urandom(24) 
CORS(app)

graph = db_auth() #connect to neo4j



@app.route('/', methods=['GET'])
def ind():
    return "It's working man"

@app.route('/accounts/register', methods=['GET'])
def register_get():
    return render_template("accounts/register.html")


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
        # get recommended users from postgresSQL
        # uid_list1 = recommend_user_by_equipment(str(get_uid(usr)))
        # random.shuffle(uid_list1)
        # new_uid_list1 = []
        # L1 = []
        # for uid in uid_list1:
        #     if check_is_friend(usr, uid[0]) == 0:
        #         new_uid_list1.append(uid)
        # L1 = get_user_info(new_uid_list1)
        # L1 = L1[:3]

        # get recommended users from the users share the same interest target
        # 1. get user interested targets
        # targets = get_user_interest(usr)
        # random.shuffle(targets)
        # 2. get a non-friend user from each target with max 6 users
        # uid_list2 = []
        # L2 = []
        # for t in targets:
        #     uid = get_a_new_user(usr, int(t['TID']))
        #     if uid != -1:
                
        #         uid_list2.append([uid])
        #     if len(uid_list2) > 3:
        #         break
        # print(uid_list2)
        # if len(uid_list2) != 0:
        #     L2 = get_user_info(uid_list2)
        # if len(L2) > 3:
        #     L2 = L2[:3]
        # get recommended users from the users in the same project
        # filter out the users that already is friend
        # recommended_user = L1+L2
        # uid_rest = []
        # if len(recommended_user) < 6:
        #     need = 6-len(recommended_user)
        #     for i in range(need):
        #         while True:
        #             uid = random.randint(0, count_user())
        #             if uid != get_uid(usr):
        #                 break
        #         uid_rest.append([uid])
        # L3 = get_user_info(uid_rest)
        
        # recommended_user = L1+L2+L3

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
    # if request.headers['user']:
    #     usr = request.headers['user']
    #     session["usr"] = usr
    user_profile = get_profile("Ohputlm@Observatory229.com")
    projects = get_project_join("Ohputlm@Observatory229.com")
    return {'user_profile':user_profile,'projects':projects}
        #return render_template("accounts/joinedProjects.html", user_profile=user_profile, projects = projects)
    # else:
    #     return "login"
        #return redirect(url_for("login_get"))

@app.route('/accounts/manageprojects', methods=['GET'])
def manageProject():
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        projects = user_manage_projects_get(usr)
        return {'user_profile':user_profile, 'projects':projects}
        #return render_template("accounts/manageprojects.html", user_profile=user_profile, projects = projects)
    else:
        return "login"
        #return redirect(url_for("login_get"))

# 0331 show the ranking of users' joined projects
@app.route('/accounts/rankedProjects', methods=['GET'])
def getRankedProjects():
    # get user customized ranking frome database
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        projects = get_project_orderby_priority(usr)
        return {'user_profile':user_profile, 'projects':projects}
        #return render_template("accounts/joinedProjects.html", user_profile=user_profile, projects = projects)
    else:
        return "login"
        #return redirect(url_for("login_get"))

# 0331 for users to rank their joined projects
@app.route('/accounts/rankedProjects', methods=['POST'])
def postRankedProjects():
    # get user customized ranking
    ''' TODO '''
    pid_list = []
    # expected a PID list

    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        user_profile = get_profile(usr)
        
        # only when user click the save button would update the database
        if request.form.get('button') == 'save':
            upadte_project_priority(usr, pid_list)

        if request.form.get('button') == 'reset':
            projects = get_project_join(usr)
            projects = get_project_default_priority(projects)

        return {'user_profile':user_profile, 'projects':projects}
        #return render_template("accounts/joinedProjects.html", user_profile=user_profile, projects = projects)
    else:
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
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        hid = request.json['PID'].strip()
        project_target = get_project_target(int(hid))
        return jsonify(project_targets = project_target)
    else:
        return "login"
        #return redirect(url_for("login_get"))


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
        return jsonify(generate_default_schedule(usr, uhaveid))
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
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        '''TODO'''
        if request.form.get('button') == 'update':            
            hid = request.json['uhaveid'].strip() 
            print(hid)
            user_equipments = update_user_equipments(aperture,Fov,pixel_scale,tracking_accuracy,lim_magnitude,elevation_lim,mount_type,camera_type1,
            camera_type2,JohnsonB,JohnsonR,JohnsonV,SDSSu,SDSSg,SDSSr,SDSSi,SDSSz,
            usr,Site,Longitude,Latitude,Altitude,tz,daylight,wv,light_pollution,int(hid))
        if request.form.get('button') == 'add':
            equipments = create_equipments(aperture,Fov,pixel_scale,tracking_accuracy,lim_magnitude,elevation_lim,mount_type,camera_type1,camera_type2,JohnsonB,JohnsonR,JohnsonV,SDSSu,SDSSg,SDSSr,SDSSi,SDSSz)
            print(equipments.EID)
            user_equipments = create_user_equipments(usr,equipments.EID,Site,Longitude,Latitude,Altitude,tz,daylight,wv,light_pollution)
            # create spatial user equipment
            # postgres_create_user_equipments(int(user_equipments.id),get_uid(usr), equipments.EID,Longitude,Latitude,Altitude)
        if request.form.get('button') == 'delete':            
            hid = request.json['uhaveid'].strip() 
            delete_user_equipment(usr,int(hid))
            # delete user's equipment in postgresSQL
            postgres_delete_user_equipments(int(hid))
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
    text = request.json['search'].strip()
    # text = '(?i).*'+text+'.*'
    print(text)
    # if request.form.get('button') == 'Search':
    # target = search_target(text)
    target = query_from_simbad(text)

    #return render_template("projects/search_target.html", target = target)
    return jsonify(target = target)

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
    aperture_upper_limit = request.json['aperture_upper_limit'].strip()
    aperture_lower_limit = request.json['aperture_lower_limit'].strip()
    FoV_upper_limit = request.json['FoV_upper_limit'].strip()
    FoV_lower_limit = request.json['FoV_lower_limit'].strip()
    pixel_scale_upper_limit = request.json['pixel_scale_upper_limit'].strip()
    pixel_scale_lower_limit = request.json['pixel_scale_lower_limit'].strip()
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
    if "usr" in session:
        usr = session["usr"]
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
@app.route('/projects/addTarget', methods=['POST'])
def addTarget():
    PID = request.json['PID'].strip()
    TID = request.json['TID'].strip()
    JohnsonB = request.json['JohnsonB'].strip()
    JohnsonV = request.json['JohnsonV'].strip()
    JohnsonR = request.json['JohnsonR'].strip()
    SDSSu = request.json['SDSSu'].strip()
    SDSSg = request.json['SDSSg'].strip()
    SDSSr = request.json['SDSSr'].strip()
    SDSSi = request.json['SDSSi'].strip()
    SDSSz = request.json['SDSSz'].strip()
    if "usr" in session:
        usr = session["usr"]
        session["usr"] = usr
        target  = create_project_target(usr,int(PID),int(TID),JohnsonB, JohnsonR, JohnsonV, SDSSu, SDSSg, SDSSr, SDSSi, SDSSz)
        return jsonify(target = target)
    else:
        return "login"
        # return redirect(url_for("login_get"))

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


@app.route('/accounts/logout')
def logout():
    session.pop("usr", None)
    flash("You have successfully been logged out.", "info")
    return "login"
    # return redirect(url_for("login_get"))


if __name__ == '__main__':
    app.run(debug=True)