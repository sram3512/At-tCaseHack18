from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import datetime,json
from datetime import date
import time
from time import mktime,localtime
from flask import Flask,request,Response
from pytz import timezone
app = Flask(__name__)

@app.route("/",methods=['GET','POST'])
def gcal_lookup():
    jdata=json.loads(request.data.decode("utf-8"))
    sleeptime=jdata['sleeptime']
    showpref=list(jdata['show_pref'])
    bglimit=int(jdata['binge_limit'])
    dtsplit=str(date.today()).split('-')
    #tim1=time.localtime()
    #tim2=datetime.datetime.strptime(dtsplit[0]+"/"+dtsplit[1]+"/"+dtsplit[2]+" 23:00:00.000000","%Y/%m/%d %H:%M:%S.%f")
    #print (tim2-tim2)
    #print (time.strftime("%H:%M:%S",sleeptime))
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
    print (limit)
    print (now)
    events_result = service.events().list(calendarId='primary',timeMin=now,timeMax=limit,maxResults=10, singleEvents=True,orderBy='startTime').execute()
    events = events_result.get('items', [])
    blocked=[]
    #0 number of events since
    for schedules in events:
        #2018-09-28T13:30:00-07:00
        st=time.strftime("%H:%M",time.strptime(schedules['start']['dateTime'],"%Y-%m-%dT%H:%M:%S-07:00")).replace(':','')
        ed=time.strftime("%H:%M",time.strptime(schedules['end']['dateTime'],"%Y-%m-%dT%H:%M:%S-07:00")).replace(':','')
        blocked.append((int(st),int(ed)))
    print (blocked)
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
    print (range_beg,range_end)
    while range_beg<=range_end:
        if len(blocked)!=0:
            for elem in blocked:
                if range_beg!=elem[0]:
                    avb_slots.append((range_beg,range_beg+step))
        else:
            avb_slots.append((range_beg,range_beg+step))
        range_beg+=step
    print (avb_slots[:bglimit])
    output={}
    for element in avb_slots[:bglimit]:
        output[str(element)]=showpref[0]
        #should do db lookup to track user watch preference and time comparision
    rs =Response(json.dumps(output),status=200,mimetype="application/json")
    return rs
