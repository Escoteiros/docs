import collections
import datetime
import json
import os
import sys

import httpx

def get_timestamp():
    dt = datetime.datetime.now(datetime.timezone.utc)
    utc_time = dt.replace(tzinfo=datetime.timezone.utc)
    return int(utc_time.timestamp())

def from_timestamp(timestamp: int)->datetime.datetime:
    dt = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)
    return dt.replace(second=0, microsecond=0)    

URLS = ['https://github.com', 'https://paxtu.escoteiros.org.br',
        'https://escoteiros.org.br', 'https://paxtu.escoteiros.org.br/naoexiste']

data_file = os.path.abspath(
    'uptime.json' if not len(sys.argv) > 1 else sys.argv[1])
uptime_md_file = os.path.abspath(
    'docs/uptime.md' if not len(sys.argv) > 2 else sys.argv[2])

print('Reading data file:', data_file)
try:
    with open(data_file) as file:
        uptime_data = json.load(file)
        print('Uptime data readen: ', len(uptime_data), ' domains')
except Exception as exc:
    print('Failed to read uptime data', exc)
    uptime_data = {}


def check_url(url: str) -> int:
    try:
        r = httpx.get(url, follow_redirects=True)
        return r.status_code

    except httpx.HTTPStatusError as e:
        return e.response.status_code

    except Exception as e:
        print(e)

    return 0


def get_data_statuses(data):
    last_24h = (datetime.datetime.utcnow()-datetime.timedelta(days=1)
                ).replace(second=0, microsecond=0)
    old_statuses = collections.defaultdict(list)
    statuses = {}
    for (timestamp, status_code) in data:
        dt = from_timestamp(timestamp)
        if dt < last_24h:
            old_statuses[dt.date()].append(status_code)
        else:
            statuses[dt] = status_code

    last_days = sorted(old_statuses.keys())[-7:]
    last_days_statuses = ''
    for last_day in last_days:
        success, fails = 0, 0

        for status_code in old_statuses[last_days]:
            if 0 < status_code < 400:
                success += 1
            else:
                fails += 1

        msg = []
        if success > 0:
            msg.append(f'OK={success}')
            if fails == 0:
                icon = '✔️'
            else:
                msg.append(f'Falhas={fails}')
                icon = '⚠️'
        elif fails > 0:
            msg.append(f'Falhas={fails}')
            icon = '❌'
        else:
            icon = '⌛'
        title = ', '.join(msg)
        last_days_statuses += f'<span title="{last_day}: {title}">{icon}</span>'

    today_times = sorted(statuses.keys())
    today_statuses = ''
    for t in today_times:
        icon = '✔️' if 0 < statuses[t] < 400 else '❌'
        today_statuses += f'<span title="{t} : {statuses[t]}">{icon}</span>'

    return f'{last_days_statuses}|{today_statuses}'


for url in URLS:
    result = (get_timestamp(), check_url(url))
    if url not in uptime_data:
        uptime_data[url] = []

    uptime_data[url].append(result)
    print(f'URL {url} -> {result[1]} ({len(uptime_data[url])})')

try:
    with open(data_file, 'w') as file:
        json.dump(uptime_data, file)
        print('Uptime data written: ', len(uptime_data), ' domains')
except Exception as exc:
    print('Failed to write uptime data', exc)

print('Saving markdown ', uptime_md_file)
with open(uptime_md_file, 'w') as file:
    file.write(
        f'# Monitoramento\n\nÚltima verificação: {datetime.datetime.utcnow()}\n\n')
    file.write('|Serviço|Status|Últimas 24h|\n|---|---|---|\n')
    for url, data in uptime_data.items():
        file.write(f'|{url}|{get_data_statuses(data)}|\n')
