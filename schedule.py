from data.db_session import db_auth
from datetime import timedelta
import os, uuid, pathlib
import random
import numpy as np
import threading, time, signal
from services.schedule_service import generate_default_schedule

# For sending email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from string import Template
from pathlib import Path
import smtplib

graph = db_auth() #connect to neo4j

class ProgramKilled(Exception):
    pass

def signal_handler(signum, frame):
    raise ProgramKilled

class Job(threading.Thread):
    def __init__(self, interval, execute, *args, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = False
        self.stopped = threading.Event()
        self.interval = interval
        self.execute = execute
        self.args = args
        self.kwargs = kwargs
        
    def stop(self):
                self.stopped.set()
                self.join()
    def run(self):
            while not self.stopped.wait(self.interval.total_seconds()):
                self.execute(*self.args, **self.kwargs)

def daily():
    print("generating schedule.....", time.ctime())
    # query all user 
    query = "MATCH (n:user) return n.email as usr, n.name as name  ORDER by n.UID DESC"
    users = graph.run(query).data()

    for i in range(len(users)):
        email = users[i]['usr']
        name = users[i]['name']
        print("generate schedule for ", name, ", ", email)
        query = "MATCH (n:user{email:$email})-[rel:UhaveE]->(e:equipments) return rel.uhaveid as uhaveid"
        equipments = graph.run(query, email=email).data()
        for j in range(len(equipments)):
            generate_default_schedule(users[i]['usr'], equipments[j]['uhaveid'])
    # Send notification email to user
        # send_email(name, email)

def send_email(name, email):
    content = MIMEMultipart()
    content["subject"] = "New Schedule Arranged by Spacelink!"
    content["from"] = "e94056013@gmail.com"
    content["to"] = email
    # content.attach(MIMEText("↓↓↓ Click the link down below to check out your new schedule tonight! ↓↓↓"))

    template = Template(Path("mail/email_template.html").read_text())
    body = template.substitute({"name": name})

    content.attach(MIMEText(body, "html"))

    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.login("spacelink@gmail.com", "abcdefghijklmnop")
            smtp.send_message(content)
            print("Complete!")
        except Exception as e:
            print("Error message: ", e)

def foo():
    print(time.ctime())
    
# period of generating schedule
WAIT_TIME_SECONDS = 300

if __name__ == '__main__':
    #start scheduling in initial then period scheduling 
    daily()
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    job = Job(interval=timedelta(seconds=WAIT_TIME_SECONDS), execute=daily)
    job.start()
    
    while True:
        try:
            time.sleep(1)
        except ProgramKilled:
            print("Program killed: running cleanup code")
            job.stop()
            break
