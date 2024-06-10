import collections
import datetime
import http.client
import json
import os
import sys
import zoneinfo

import httpx

ziBR = zoneinfo.ZoneInfo('America/Sao_Paulo')


class DataHora():

    def __init__(self, obj=None):
        self._dh = (datetime.datetime
                    .now()
                    .astimezone(datetime.timezone.utc))
        if isinstance(obj, int):
            self._dh = datetime.datetime.fromtimestamp(
                obj, tz=datetime.timezone.utc)
        elif isinstance(obj, datetime.datetime):
            if obj.tzinfo:
                if obj.tzinfo == datetime.timezone.utc:
                    self._dh = obj
                else:
                    self._dh = obj.astimezone(datetime.timezone.utc)
        self._dh = self._dh.replace(second=0, microsecond=0)

    def __str__(self) -> str:
        return self._dh.astimezone(ziBR).strftime('%d/%m/%Y %H:%M:%S %Z')

    def __lt__(self, other):
        return self._dh < other._dh

    def sub(self, interval: datetime.timedelta):
        self._dh -= interval
        return self

    def date(self) -> datetime.date:
        return self._dh.date()

    def timestamp(self) -> int:
        return int(self._dh.timestamp())


def try_paxtu_login() -> int:
    if payload := os.getenv('PAXTU_LOGIN_PAYLOAD'):
        print('Verificando login paxtu')
    else:
        print('Ignorando login paxtu (PAXTU_LOGIN_PAYLOAD inexistente)')
        return 0

    conn = http.client.HTTPSConnection("paxtu.escoteiros.org.br")

    headers = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
        'Accept': "*/*",
        'Accept-Language': "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
        'Accept-Encoding': "gzip, deflate, br",
        'X-Requested-With': "XMLHttpRequest",
        'Content-Type': "application/x-www-form-urlencoded",
        'Origin': "https://paxtu.escoteiros.org.br",
        'DNT': "1",
        'Alt-Used': "paxtu.escoteiros.org.br",
        'Connection': "keep-alive",
        'Referer': "https://paxtu.escoteiros.org.br/meupaxtu/",
        'Cookie': "JSESSIONID=E7EFEE3A1D2EB08F2A492D874DFFB8A8; _ga_2CK8L0JG1X=GS1.1.1691107443.5.1.1691108008.0.0.0; _ga=GA1.3.740541310.1687381654; _ga_79Y7FBF0P0=GS1.1.1691107443.5.1.1691108008.0.0.0",
        'Sec-Fetch-Dest': "empty",
        'Sec-Fetch-Mode': "cors",
        'Sec-Fetch-Site': "same-origin",
        'TE': "trailers"
    }

    try:
        conn.request("POST", "/meupaxtu/loginMeuSigue.do", payload, headers)

        res = conn.getresponse()

        _ = res.read()

        return res.status
    except Exception as exc:
        print(exc)
        return 500


URLS = ['https://github.com', 'https://paxtu.escoteiros.org.br',
        'https://escoteiros.org.br', 'https://paxtu.escoteiros.org.br/paxtu',
        'https://paxtu.escoteiros.org.br/meupaxtu','https://sigue.escoteiros.org.br/siguenacional',
        'https://id.escoteiros.org.br/']

data_file = os.path.abspath(
    'uptime.json' if len(sys.argv) <= 1 else sys.argv[1]
)
uptime_md_file = os.path.abspath(
    'uptime.md' if len(sys.argv) <= 2 else sys.argv[2]
)

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
    last_24h = DataHora().sub(datetime.timedelta(days=1))

    old_statuses = collections.defaultdict(list)
    statuses = {}
    for (timestamp, status_code) in data:
        dt = DataHora(timestamp)
        if dt < last_24h:
            old_statuses[dt.date()].append(status_code)
        else:
            statuses[dt] = status_code

    last_days = sorted(old_statuses.keys())[-7:]
    last_days_statuses = ''
    for last_day in last_days:
        success, fails = 0, 0

        for status_code in old_statuses[last_day]:
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


PAXTU_LOGIN = 'Paxtu Login'

for url in URLS:
    result = (DataHora().timestamp(), check_url(url))
    if url not in uptime_data:
        uptime_data[url] = []

    uptime_data[url].append(result)

    print(f'URL {url} -> {result[1]} ({len(uptime_data[url])})')

if PAXTU_LOGIN not in uptime_data:
    uptime_data[PAXTU_LOGIN] = []
pl_ts = DataHora().timestamp()
pl_res = try_paxtu_login()
uptime_data[PAXTU_LOGIN].append((pl_ts, pl_res))
print(f'PAXTU LOGIN -> {pl_res} ({len([PAXTU_LOGIN])})')

try:
    with open(data_file, 'w') as file:
        json.dump(uptime_data, file)
        print('Uptime data written: ', len(uptime_data), ' domains')
except Exception as exc:
    print('Failed to write uptime data', exc)

print('Saving markdown ', uptime_md_file)
with open(uptime_md_file, 'w') as file:
    file.write(
        f'# Monitoramento\n\nÚltima verificação: {DataHora()}\n\n')
    file.write('|Serviço|Status|Últimas 24h|\n|---|---|---|\n')
    for url in URLS+[PAXTU_LOGIN]:
        if data := uptime_data.get(url):
            file.write(f'|{url}|{get_data_statuses(data)}|\n')
