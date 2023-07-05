import datetime
import json
import os
import time

import schedule
from fastchat.constants import LOGDIR
import requests

def get_conv_log_filename():
    t = datetime.datetime.now()
    name = os.path.join(LOGDIR, f"{t.year}-{t.month:02d}-{t.day:02d}-conv.json")
    return name

es_url = "https://localhost:9200"
index="test2"
username = "elastic"
password = "e4uwp3kZm6maRubko8g0"
data_list = []

def bulk_index_log_data():
    with open(get_conv_log_filename(), 'r') as fout:
        for line in fout:
            json_object = json.loads(line)
            if json_object not in data_list:
                data_list.append(json_object)
    bulk_data = ""
    for i, data in enumerate(data_list):
        bulk_data += json.dumps({"index": {"_id": i+1}}) + "\n"
        bulk_data += json.dumps(data) + "\n"
    response = requests.post(f"{es_url}/{index}/_bulk", headers={"Content-Type": "application/json"}, data=bulk_data, auth=(f"{username}", f"{password}"), verify=False)
    print(response.content)

def schedule_bulk_index(seconds):
    schedule.every(seconds).seconds.do(bulk_index_log_data)

while True:
    bulk_index_log_data()
    time.sleep(5)
