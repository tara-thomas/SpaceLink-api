from py2neo.ogm import GraphObject, Property, RelatedTo, RelatedFrom, RelatedObjects


class User(GraphObject):
    __primarylabel__ = "user"
    __primarykey__ = "email"
    UID = Property()
    username = Property()
    name = Property()
    email = Property()
    password = Property()
    affiliation = Property()
    title = Property()
    country = Property()
    hashed_password = Property()
    created_on = Property()
    last_logon = Property()
    UhaveE = RelatedTo("Equipments","OWNER")
    Manage = RelatedTo("Projects","OWN")   

class Equipments(GraphObject):
    __primarylabel__ = "equipments"
    __primarykey__ = "EID"
    EID = Property()
    telName = Property()
    focalLength = Property()
    diameter = Property()
    camName = Property()
    pixelSize = Property()
    sensorW = Property()
    sensorH = Property()
    camera_type1 = Property()
    camera_type2 = Property()
    # lFilter = Property()
    # rFilter = Property()
    # gFilter = Property()
    # bFilter = Property()
    # haFilter = Property()
    # oiiiFilter = Property()
    # siiFilter = Property()
    # duoFilter = Property()
    # multispectraFilter = Property()
    # JohnsonU = Property()
    # JohnsonB = Property()
    # JohnsonV = Property()
    # JohnsonR = Property()
    # JohnsonI = Property()
    # SDSSu = Property()
    # SDSSg = Property()
    # SDSSr = Property()
    # SDSSi = Property()
    # SDSSz = Property()
    filterArray = Property()
    mountName = Property()
    mount_type = Property()
    deg = Property()
    barlowName = Property()
    magnification = Property()
    focalRatio = Property()
    fovDeg = Property()
    resolution = Property()
    project_priority = Property() # 0921
    owner = RelatedFrom(User,"UHAVEE")

class Target(GraphObject):
    __primarylabel__ ="target"
    __primarykey__ ="TID"
    TID = Property()
    name = Property()
    longitude = Property()
    latitude = Property()

class Project(GraphObject):
    __primarylabel__ = "project"
    __primarykey__ = "PID"
    PID = Property()
    project_type = Property()
    title = Property()
    PI = Property()
    description = Property()
    FoV_lower_limit = Property()
    resolution_upper_limit = Property()
    required_camera_type = Property()
    required_filter = Property()
    own = RelatedFrom(User, "MANAGE")

class Schedule(GraphObject):
    __primarylabel__ = "schedule"
    __primarykey__ = "SID"
    SID = Property()
    last_update = Property()
    observe_section = Property()
