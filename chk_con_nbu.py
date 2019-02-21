import logging
import os.path
import platform
import socket
import subprocess
import threading
from math import ceil
from optparse import OptionParser
from sys import exit, stdout

is_win = True if platform.system() == 'Windows' else False
bin_admin_path = r'C:\Program Files\Veritas\NetBackup\bin\admincmd' if is_win else r'/usr/openv/netbackup/bin/admincmd'
BPGETCONFIG = r'bpgetconfig.exe' if is_win else r'bpgetconfig'
FORMAT = 'thread %(thread)d: %(message)s '

PBX_PORT = 1556
BPCD_PORT = 13724

usage = "usage: %prog [options] host1 host2 host3 ..."
parser = OptionParser(usage)

parser.add_option("-f", "--file", dest="filename",
                  help="read hosts from file, one per line;")
parser.add_option("-b", "--bin_admin",
                  dest="bin_admin", default=bin_admin_path,
                  help="path to .../netbackup/bin/admincmd")
parser.add_option("-s", "--skip_bpgetconfig", action="store_true",
                  dest="skip_bpgetconfig", default=False,
                  help="Don't run bpgetconfig to confirm connection")
parser.add_option("-n", "--num_threads",
                  dest="num_threads", default=100, type=int
                  help="number of threads to run simultaneously")
parser.add_option("-v", "--verbose",
                  action="store_true", dest="verbose", default=False,
                  help="print status messages to stdout")
parser.add_option("-d", "--debug",
                  action="store_true", dest="debug", default=False,
                  help="print debug messages to stdout")

(options, args) = parser.parse_args()
hosts = args
result = []

if options.debug:
    logging.basicConfig(stream=stdout, format=FORMAT, level=logging.DEBUG)
else:
    if options.verbose:
        logging.basicConfig(stream=stdout, format=FORMAT, level=logging.INFO)
    else:
        logging.basicConfig(stream=stdout, format=FORMAT, level=logging.WARN)

if options.filename:
    if os.path.isfile(options.filename):
        with open(options.filename) as f:
            hosts = hosts + f.read().splitlines()

if len(hosts) == 0:
    logging.critical('No hosts were provided for a check')
    exit(1)

if not options.skip_bpgetconfig:
    if not os.path.isfile(os.path.join(options.bin_admin, BPGETCONFIG)):
        logging.critical("Can't find bpgetconfig in {0}".format(options.bin_admin))
        exit(1)


def split(arr, size):
    arrs = []
    while len(arr) > size:
        pice = arr[:size]
        arrs.append(pice)
        arr = arr[size:]
    arrs.append(arr)
    return arrs


class Host(object):
    def __init__(self, host):
        self.name = host
        self.pbx = True
        self.bpcd = True
        self.bpgetconfig = True

    @property
    def partial(self):
        return not self.complete and self.failed

    @property
    def failed(self):
        return not self.pbx or not self.bpcd or not self.bpgetconfig

    @property
    def complete(self):
        return not self.pbx and not self.bpcd and not self.bpgetconfig

    def report(self):
        if not self.failed:
            print 'host {0} was reachable'.format(self.name)
        else:
            if self.complete:
                print 'host {0} was completely unreachable'.format(self.name)
            else:
                print 'host {0} was partially unreachable bpcd: {1}, pbx {2}, bpgetconfig {3}'.format(
                    self.name,
                    'OK' if self.bpcd else 'FAILED',
                    'OK' if self.pbx else 'FAILED',
                    'OK' if self.bpgetconfig else 'FAILED')


def test_soc(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    logging.info("testing connection to {0} port {1}".format(host, port))
    try:
        if sock.connect_ex((host, port)) == 0:
            sock.close()
            return True
        else:
            sock.close()
            return False
    except Exception:
        return False


def check_nbu_port(task_list):
    for h in task_list:
        host = Host(h)
        host.pbx = test_soc(host.name, PBX_PORT)
        host.bpcd = test_soc(host.name, BPCD_PORT)
        if not options.skip_bpgetconfig:
            try:
                with open(os.devnull, 'w') as FNULL:
                    out = subprocess.Popen([os.path.join(options.bin_admin, BPGETCONFIG), "-M", host.name],
                                           stdout=subprocess.PIPE, stderr=FNULL).communicate()[0].strip()
                logging.debug("bpgetconfig from {0} returned >>{2}{1}{2}<<".format(host, out, os.linesep))
                if len(out) == 0:
                    host.bpgetconfig = False
            except subprocess.CalledProcessError:
                host.bpgetconfig = False
        else:
            logging.info('bpgetconfig test was skipped for {0}'.format(host.name))
        result.append(host)
    return


threads = []

if __name__ == '__main__':
    part_hosts = split(hosts, int(ceil(float(len(hosts)) / options.num_threads)))

    for task_list in part_hosts:
        t = threading.Thread(target=check_nbu_port, args=(task_list,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    for host in result:
        host.report()
