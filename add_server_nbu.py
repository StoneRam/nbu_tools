import logging
import os
import os.path
import platform
import subprocess
import threading
from math import ceil
from optparse import OptionParser
from sys import exit, stdout

FORMAT = 'thread %(thread)d: %(message)s '
is_win = True if platform.system() == 'Windows' else False
bin_admin_path = r'C:\Program Files\Veritas\NetBackup\bin\admincmd' if is_win else r'/usr/openv/netbackup/bin/admincmd'
BPGETCONFIG = r'bpgetconfig.exe' if is_win else r'bpgetconfig'
BPSETCONFIG = r'bpsetconfig.exe' if is_win else r'bpsetconfig'

usage = "usage: %prog [options] host1 host2 host3 ..."
parser = OptionParser(usage)

parser.add_option("-f", "--file", dest="host_list_file",
                  help="read hosts from file, one per line;")
parser.add_option("-s", "--server", dest="server_file", default=None,
                  help="read new server entries from file, bp.conf syntax SERVER = HOSTNAME")
parser.add_option("-b", "--bin_admin",
                  dest="bin_admin", default=bin_admin_path,
                  help="path to .../netbackup/bin/admincmd")
parser.add_option("-n", "--num_threads",
                  dest="num_threads", default=100,
                  help="number of threads to run simultaneously")
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="print status messages to stdout")
parser.add_option("-d", "--debug",
                  action="store_true", dest="debug", default=False,
                  help="print debug messages to stdout")

(options, args) = parser.parse_args()
hosts = args

servers = []

bpgetconfig_path = os.path.join(os.path.join(options.bin_admin, BPGETCONFIG))
bpsetconfig_path = os.path.join(os.path.join(options.bin_admin, BPSETCONFIG))

if options.debug:
    logging.basicConfig(stream=stdout, format=FORMAT, level=logging.DEBUG)
else:
    if options.verbose:
        logging.basicConfig(stream=stdout, format=FORMAT, level=logging.INFO)
    else:
        logging.basicConfig(stream=stdout, format=FORMAT, level=logging.WARN)

if options.host_list_file:
    if os.path.isfile(options.host_list_file):
        with open(options.host_list_file) as f:
            hosts = hosts + f.read().splitlines()

if os.path.isfile(options.server_file):
    with open(options.server_file) as f:
        servers = f.read().splitlines()
        servers = filter(None, servers)
    for entry in servers:
        if entry[:9] != 'SERVER = ':
            logging.critical("Entry >>{0}<< doesn't have >>SERVER = << in it".format(entry))
            exit(1)
else:
    logging.critical("Can't find server file {0}".format(options.server_file))
    exit(1)

if len(hosts) == 0:
    logging.critical('No hosts were provided for a check')
    exit(1)

if not os.path.isfile(bpgetconfig_path):
    logging.critical("Can't find bpgetconfig in {0}".format(options.bin_admin))
    exit(1)

if not os.path.isfile(bpsetconfig_path):
    logging.critical("Can't find bpsetconfig in {0}".format(options.bin_admin))
    exit(1)


def split(arr, size):
    arrs = []
    while len(arr) > size:
        pice = arr[:size]
        arrs.append(pice)
        arr = arr[size:]
    arrs.append(arr)
    return arrs


def add_nbu_server(host):
    out = ''
    with open(os.devnull, 'w') as FNULL:
        try:
            logging.info("Getting config from host {0}".format(host))
            out = subprocess.Popen([bpgetconfig_path, "-M", host],
                                   stdout=subprocess.PIPE, stderr=FNULL).communicate()[0].strip()
        except subprocess.CalledProcessError:
            logging.warn("Can't reach host {0}".format(host))
        if len(out) != 0:
            logging.debug("Config for host {0} was >>{2}{1}{2}<<".format(host, out, os.linesep))
            host_servers = filter(lambda x: x[:9] == 'SERVER = ', out.splitlines())
            host_servers += servers
            host_servers = [ii for n, ii in enumerate(host_servers) if ii not in host_servers[:n]]  # remove duplicates
            host_servers = os.linesep.join(host_servers)
            logging.debug("Setting servers to >>{0}<< for host {1}".format(host, host_servers))
            subprocess.Popen([bpsetconfig_path, '-h', host], stdout=FNULL, stdin=subprocess.PIPE,
                             stderr=FNULL).communicate(
                input=host_servers)
            logging.info("Config for host {0} was updated".format(host))
            try:
                logging.info("Verifying that host {0} reachable after update".format(host))
                out = subprocess.Popen([bpgetconfig_path, "-M", host],
                                       stdout=subprocess.PIPE, stderr=FNULL).communicate()[0].strip()
                if len(out) == 0:
                    logging.critical("After updating config on host {0} became unreachable. Aborting...".format(host))
                    os._exit(1)  # stop all threads
                else:
                    logging.info("Host {0} is reachable after update. OK.".format(host))
                    print '{0} config was updated successfully'.format(host)
            except subprocess.CalledProcessError:
                logging.critical("After updating config on host {0} became unreachable. Aborting...".format(host))
                os._exit(1)  # stop all threads
        else:
            logging.warn("Can't reach host {0}".format(host))


def add_server_hosts(task_list):
    for host in task_list:
        add_nbu_server(host)


threads = []

if __name__ == '__main__':
    part_hosts = split(hosts, int(ceil(float(len(hosts)) / options.num_threads)))

    for task_list in part_hosts:
        t = threading.Thread(target=add_server_hosts, args=(task_list,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
