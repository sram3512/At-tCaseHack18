from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import datetime,json
from datetime import date
import time
from time import mktime,localtime
from flask import Flask,request,Response
from pytz import timezone
from flask_cors import CORS
import requests,json
app = Flask(__name__)

CORS(app)
def fetchEpisode():
    with open('serials') as f:
        data = json.load(f)
    if len(data["ToView"]["Game of Thrones"]["Season 2"]) >0:
        key_vals= data["ToView"]["Game of Thrones"]["Season 2"].keys()
        f = map(lambda x: int(x.replace('S','').replace('E','')),key_vals)
        f=list(f)
        f.sort()
        ep=str(int(f[0]/100))
        episode="S0"+ep+"E0"+str(int(f[0])%100)
        del data["ToView"]["Game of Thrones"]["Season 2"][episode]
        with open('serials', 'w') as outfile:
            json.dump(data, outfile)
        return "Game of Thrones - " + episode

@app.route("/",methods=['GET','POST'])
def gcal_lookup():
    jdata=json.loads(request.data.decode("utf-8"))
    sleeptime=jdata['sleeptime']
    showpref=list(jdata['show_pref'])
    bglimit=int(jdata['binge_limit'])
    dtsplit=str(date.today()).split('-')
    SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json',SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))
    dtsplit=str(date.today()).split('-')


    limit=timezone('US/Pacific').localize(datetime.datetime.strptime(dtsplit[0]+"/"+dtsplit[1]+"/"+dtsplit[2]+" "+sleeptime,"%Y/%m/%d %H:%M:%S")).astimezone(timezone('UTC')).isoformat().split('+')[0]+".000000Z"
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(calendarId='primary',timeMin=now,timeMax=limit,maxResults=10, singleEvents=True,orderBy='startTime').execute()
    events = events_result.get('items', [])
    blocked=[]
    for schedules in events:
        st=time.strftime("%H:%M",time.strptime(schedules['start']['dateTime'],"%Y-%m-%dT%H:%M:%S-07:00")).replace(':','')
        ed=time.strftime("%H:%M",time.strptime(schedules['end']['dateTime'],"%Y-%m-%dT%H:%M:%S-07:00")).replace(':','')
        blocked.append((int(st),int(ed)))
    nwtm=datetime.datetime.now()
    range_beg=0
    if nwtm.hour!=23:
        range_beg=int(nwtm.hour)+1
        range_beg*=100
    range_beg=1600
    tmp_splt=sleeptime.split(':')
    range_end=int(tmp_splt[0]+tmp_splt[1])
    avb_slots=[]
    step=100
    while range_beg<=range_end and range_beg!=2300:
        if len(blocked)!=0:
            for elem in blocked:
                if range_beg!=elem[0]:
                    avb_slots.append((range_beg,range_beg+step))
        else:
            avb_slots.append((range_beg,range_beg+step))
        range_beg+=step

    SCOPES3='https://www.googleapis.com/auth/calendar'
    store=file.Storage('token3.json')
    creds=store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES3)
        creds = tools.run_flow(flow, store)

    service3 = build('calendar', 'v3', http=creds.authorize(Http()))
    str_nwtm=str(nwtm)
    output={}
    for element in avb_slots[:bglimit]:
        output[str(element)]=fetchEpisode()
        start_time=str(element[0])[:2]
        end_time=str(element[1])[:2]
        event={'summary':output[str(element)],'start':{'dateTime':str_nwtm.split(' ')[0]+'T'+start_time+':00:00-07:00','timeZone':'America/Los_Angeles',},'end':{'dateTime':str_nwtm.split(' ')[0]+'T'+end_time+':00:00-07:00','timeZone':'America/Los_Angeles',}}
        service3.events().insert(calendarId='primary',body=event).execute()


    SCOPES2='https://www.googleapis.com/auth/gmail.readonly'
    store = file.Storage('token2.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json',SCOPES2)
        creds=tools.run_flow(flow,store)
    service2 = build('gmail', 'v1', http=creds.authorize(Http()))
    results = service2.users().messages().list(userId='me',maxResults=20).execute()
    labels = results.get('labels', [])
    mail_subjects=[]
    for element in results['messages']:
        vals=service2.users().messages().get(userId='me',id=element['id'],format='metadata' ).execute()
        for els in vals['payload']['headers']:
            if els['name']=='Subject':
                r=requests.get("https://api.dandelion.eu/datatxt/cl/v1?text="+els['value'].replace(' ','+')+"&model=4cf2e1c-e48a-4c14-bb96-31dc11f84eac&token=fc1acd6575f24b60a0ae66bbb2e38fe9")
                if r.status_code==200:
                    joutput=json.loads(r.text)
                    if len(joutput['categories'])!=0:
                        mail_subjects.append(joutput['categories'][0]['name'])
    dict_mail={}
    for key in list(mail_subjects):
        dict_mail[key]=mail_subjects.count(key)
    dict_mail={"politics": 3, "economy": 1, "science-environment": 1, "technology": 12}
    output['categories']=dict_mail
    rs =Response(json.dumps(output),status=200,mimetype="application/json")
    return rs
