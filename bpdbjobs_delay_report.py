import csv
import re
from collections import defaultdict, OrderedDict
from datetime import datetime

import argparse
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from  matplotlib.dates import date2num, HourLocator, DateFormatter

MAX_TIME = 999999999999
SELECTIONS_COUNT_INDEX = 31
TRY_COUNT_INDEX = 33
STU_TRY_OFFSET = 1
SERVER_TRY_OFFSET = 2
LINES_COUNT_TRY_OFFSET = 8
LINES_TRY_OFFSET = 9
START_TIME_TRY_OFFSET = 3
ELAPSED_TIME_TRY_OFFSET = 4
END_TIME_TRY_OFFSET = 5
JOBID_OFFSET = 0
BYTES_TRY_OFFSET = 10
JOB_TYPE_OFFSET = 1
CLIENT_OFFSET = 6
POLICY_OFFSET = 4
TRY_FIELD_COUNT = 11

JOB_TYPE_BACKUP = 0
JOB_TYPE_DUPLICATE = 4

START_TIME_OFFSET = 8
END_TIME_OFFSET = 10

BPTM_DELAY = 0.015  # sec
BPBKAR_DELAY = 0.015  # sec

INTERVAL = 300  # 5 min


def valid_date(s):
    try:
        return int(datetime.strptime(s, "%Y-%m-%d-%H").timestamp())
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


parser = argparse.ArgumentParser('bpdbjobs_delay_report')
parser.add_argument('-f|--file', dest='bpdbjobs', type=str, help='file with bpdbjobs -all_columns output',
                    required=True)
parser.add_argument('-o|--output', dest='output', type=str, help='output pdf', required=True)
parser.add_argument('-i|--interval', dest='interval', type=str, help='Interval', default=INTERVAL)
parser.add_argument('-s|--start_date', dest='start_date', type=valid_date,
                    help="The Start Date - format YYYY-MM-DD-HH24", default=0)
parser.add_argument('-n|--skip_slps', action='store_true', dest='skip_slps',
                    help="Don't count SLP stats")
parser.add_argument('-y|--only_slps', action='store_true', dest='only_slps',
                    help="Only count SLP stats")
parser.add_argument('-t|--top_clients', dest='top_clients', default=10,
                    help='Number of most delayed clients to display')
parser.add_argument('-e|--end_date', dest='end_date', type=valid_date, help="The End Date - format YYYY-MM-DD-HH24",
                    default=MAX_TIME)

bpbkar_waited_msg = 'times for empty buffer'
bptm_waited_msg = 'waited for full buffer '

args = parser.parse_args()

server_lost_bptm_perf = defaultdict(lambda: defaultdict(float))  # server->interval->value
server_total_perf = defaultdict(lambda: defaultdict(float))  # server->interval->value
server_lost_bpbkar_perf = defaultdict(lambda: defaultdict(float))  # server->interval->value

client_lost_bptm_perf = defaultdict(lambda: defaultdict(float))  # client->interval->value
client_lost_bpbkar_perf = defaultdict(lambda: defaultdict(float))  # client->interval->value
client_total_perf = defaultdict(lambda: defaultdict(float))  # client->interval->value

# Graph start and stop point on X axis
init_ts = MAX_TIME
cutoff_ts = 0

with open(args.bpdbjobs, 'r', encoding='utf-8') as f:
    csv_reader = csv.reader(f, delimiter=',', escapechar="\\")
    for row in csv_reader:
        jobid = row[JOBID_OFFSET]
        client = row[CLIENT_OFFSET]
        policy = row[POLICY_OFFSET]
        operation = int(row[JOB_TYPE_OFFSET])
        if operation == JOB_TYPE_BACKUP and args.only_slps:
            continue
        if operation == JOB_TYPE_DUPLICATE and args.skip_slps:
            continue
        selections_offset = int(row[SELECTIONS_COUNT_INDEX])
        start_ts = int(row[START_TIME_OFFSET])
        end_ts = int(row[END_TIME_OFFSET])
        if not (args.start_date < start_ts < args.end_date):
            continue
        if init_ts > start_ts:
            init_ts = start_ts
        if cutoff_ts < end_ts:
            cutoff_ts = end_ts
        try_count_index = TRY_COUNT_INDEX + selections_offset
        try_count = int(row[try_count_index - 1])
        this_try_offset = try_count_index
        bpbkar_issue = False
        bptm_issue = False
        for t in range(try_count):
            stu = row[this_try_offset + STU_TRY_OFFSET]
            server = row[this_try_offset + SERVER_TRY_OFFSET]
            lines_count = int(row[this_try_offset + LINES_COUNT_TRY_OFFSET])
            start_time = int(row[this_try_offset + START_TIME_TRY_OFFSET])
            elapsed_time = int(row[this_try_offset + ELAPSED_TIME_TRY_OFFSET])
            bytes = float(row[this_try_offset + BYTES_TRY_OFFSET + lines_count])
            end_time = int(row[this_try_offset + END_TIME_TRY_OFFSET])
            try:
                throughput = bytes / elapsed_time / 1024
            except ZeroDivisionError:
                throughput = 0
            start_offset = start_time - start_time % args.interval
            for line in row[this_try_offset + LINES_TRY_OFFSET: this_try_offset + LINES_TRY_OFFSET + lines_count]:
                for i in range(start_offset, end_time, args.interval):
                    k = date2num(datetime.fromtimestamp(i))
                    server_total_perf['{} {}'.format(server, stu)][k] += throughput
                    client_total_perf[client][k] += throughput
                if line.find(bpbkar_waited_msg) != -1:
                    bpbkar_delayed = int(re.findall('delayed (\d+) times', line)[0]) * BPBKAR_DELAY
                    interval_average = throughput * bpbkar_delayed / elapsed_time
                    for i in range(start_offset, end_time, args.interval):
                        k = date2num(datetime.fromtimestamp(i))
                        server_lost_bpbkar_perf['{} {}'.format(server, stu)][k] += interval_average
                        client_lost_bpbkar_perf[client][k] += throughput * bpbkar_delayed / elapsed_time
                if line.find(bptm_waited_msg) != -1:
                    bptm_delayed = int(re.findall('delayed (\d+) times', line)[0]) * BPTM_DELAY
                    interval_average = throughput * bptm_delayed / elapsed_time
                    for i in range(start_offset, end_time, args.interval):
                        k = date2num(datetime.fromtimestamp(i))
                        server_lost_bptm_perf['{} {}'.format(server, stu)][k] += interval_average
                        client_lost_bptm_perf[client][k] += throughput * bptm_delayed / elapsed_time
            this_try_offset += TRY_FIELD_COUNT + lines_count

init_ts = init_ts - init_ts % args.interval
cutoff_ts = cutoff_ts - cutoff_ts % args.interval

# get top delayed clients
s_client_bpbkar_delay = OrderedDict()
for k, v in client_lost_bpbkar_perf.items():
    s_client_bpbkar_delay[k] = sum(v.values())
s_client_bpbkar_delay = sorted(s_client_bpbkar_delay, key=lambda x: s_client_bpbkar_delay[x], reverse=True)

s_client_bptm_delay = OrderedDict()
for k, v in client_lost_bptm_perf.items():
    s_client_bptm_delay[k] = sum(v.values())
s_client_bptm_delay = sorted(s_client_bptm_delay, key=lambda x: s_client_bptm_delay[x], reverse=True)

# prepare X axis
graph_x = [date2num(datetime.fromtimestamp(i)) for i in range(init_ts, cutoff_ts, args.interval)]


def setup_plt():
    plt.rcParams["figure.figsize"] = [float(len(graph_x)) / 30, 10]
    plt.xlabel('Date MM-DD HH24', fontsize=10)
    plt.xticks(rotation=70)
    ax = plt.gca()
    ax.xaxis.set_major_locator(HourLocator())
    ax.yaxis.grid(color='grey', linestyle='--', alpha=0.5)
    ax.xaxis.set_major_formatter(DateFormatter('%m-%d %H'))


def plt_client(client):
    total_graph_y = [client_total_perf[client][v] for v in graph_x]
    bptm_graph_y = [client_lost_bptm_perf[client][v] for v in graph_x]
    bpbkar_graph_y = [client_lost_bpbkar_perf[client][v] for v in graph_x]
    setup_plt()
    plt.xlabel('Date MM-DD HH24', fontsize=10)
    plt.xticks(rotation=70)
    plt.ylabel('Throughput MPps', fontsize=16)
    plt.plot_date(graph_x, bptm_graph_y, fmt="r-")
    plt.plot_date(graph_x, bpbkar_graph_y, fmt="g-")
    plt.plot_date(graph_x, total_graph_y, fmt="b-")
    plt.legend(['red: MBps loss form NW/Client IO', 'green: MBps loss from Media server', 'blue: Total throughput'],
               loc='upper left')
    pdf.savefig(orientation='portrait', bbox_inches='tight')
    plt.close()


with PdfPages(args.output) as pdf:
    plt.rcParams["figure.figsize"] = [float(len(graph_x)) / 30, 10]
    for i in range(10):
        try:
            client = s_client_bptm_delay[i]
        except IndexError:
            print('Only top {} client found for NW\\Client IO delays'.format(i))
            break
        plt.title('Top {} NW\Client IO delayed Client: {}'.format(i, client))
        plt_client(client)

    for i in range(10):
        try:
            client = s_client_bpbkar_delay[i]
        except IndexError:
            print('Only top {} client found for Media server delays'.format(i))
            break
        plt.title('Top {} Media server delayed Client: {}'.format(i, client))
        plt_client(client)

    for k in server_total_perf:
        bptm_graph_y = [server_lost_bptm_perf[k][v] for v in graph_x]
        bpbkar_graph_y = [server_lost_bpbkar_perf[k][v] for v in graph_x]
        total_graph_y = [server_total_perf[k][v] for v in graph_x]
        setup_plt()
        plt.title('Server STU: ' + k)
        plt.ylabel('MBps', fontsize=16)
        plt.plot_date(graph_x, bptm_graph_y, fmt="r-")
        plt.plot_date(graph_x, bpbkar_graph_y, fmt="g-")
        plt.plot_date(graph_x, total_graph_y, fmt="b-")
        plt.legend(['red: MBps Loss from Client/NW', 'green: MBps Loss from Media I\O', 'blue: total'],
                   loc='upper left')
        pdf.savefig(orientation='portrait', bbox_inches='tight')
        plt.close()
