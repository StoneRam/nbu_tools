# nbu_tools
Various tools for managing NetBackup [Releases](https://github.com/StoneRam/nbu_tools/releases)

## Connectivity tools
- [add_server_nbu](#add_server_nbu)

- [del_server_nbu](#del_server_nbu)

- [chk_con_nbu](#chk_con_nbu)

Use Cases:

- [Catalog Migration Pre-check](#use-case---catalog-migration-pre-check)


## Reporting tools

- [bpdbjobs_delay_report](#bpdbjobs_delay_report)

Use Cases:

- [Identify slow clients](#use-case---identify-slow-clients)
- [Identify oversubscribed STUs](#use-case---identify-oversubscribed-stus)

# Connectivity tools

## add_server_nbu

<p>Adds SERVER entries to configuration, similar to bundled NetBackup's 
<code>add_media_server_on_clients</code>, but more flexible and faster.</p>
<p> Issue with <code>add_media_server_on_clients</code> that it runs in single thread and if there are 
multiple unreachable clients in the domain it takes very long time to complete. And server 
list is taken from bp.conf/registry on the master server, which might be undesired in testing
or migration scenarios. </p>

Script is written for python 2.6.9 using only standard libraries. Compatible python interpreter 
is shipped with most major platforms. For convenience it was packaged with PyInstaller for 
Windows and Linux.

### Usage
<pre>
Usage: add_server_nbu.exe [options] host1 host2 host3 ...

Options:
  -h, --help            show this help message and exit
  -f HOST_LIST_FILE, --file=HOST_LIST_FILE
                        read hosts from file, one per line
  -s SERVER_FILE, --server=SERVER_FILE
                        read new server entries from file, bp.conf syntax
                        SERVER = HOSTNAME
  -b BIN_ADMIN, --bin_admin=BIN_ADMIN
                        path to .../netbackup/bin/admincmd
  -n NUM_THREADS, --num_threads=NUM_THREADS
                        number of threads to run simultaneously
  -v, --verbose         print status messages to stdout
  -d, --debug           print debug messages to stdout
</pre>

### Notes
 
<p>If client becomes unreachable after config update, script will terminate all threads and exit.</p>
<p>Debug will print whole configuration for each client, don't use it on large client sets</p>

## del_server_nbu
Deletes SERVER entries from configuration. Very similar to [add_server_nbu](#add_server_nbu)
, but instead of add servers for the provided list it will delete the from host's configuration.



### Usage
<pre>
Usage: del_server_nbu.exe [options] host1 host2 host3 ...

Options:
  -h, --help            show this help message and exit
  -f HOST_LIST_FILE, --file=HOST_LIST_FILE
                        read hosts from file, one per line
  -s SERVER_FILE, --server=SERVER_FILE
                        read new server entries from file, bp.conf syntax
                        SERVER = HOSTNAME
  -b BIN_ADMIN, --bin_admin=BIN_ADMIN
                        path to .../netbackup/bin/admincmd
  -n NUM_THREADS, --num_threads=NUM_THREADS
                        number of threads to run simultaneously
  -v, --verbose         print status messages to stdout
  -d, --debug           print debug messages to stdout
</pre>

### Notes
 
<p>If client becomes unreachable after config update, script will terminate all threads and exit.</p>
<p>Debug will print whole configuration for each client. Don't use it on large client sets
as it will flood output.</p>

## chk_con_nbu

<p>Checks client connectivity by connecting to NetBackup's PBX(1556), BPCD(13724) ports and 
executing <code>bpgetconfig</code>. Advantage over <code>bptestbpcd</code> and 
<code>bptestnetconn</code> is flexibility in client selection and performance. 

### Usage
<pre>
Usage: chk_con_nbu.exe [options] host1 host2 host3 ...

Options:
  -h, --help            show this help message and exit
  -f FILENAME, --file=FILENAME
                        read hosts from file, one per line;
  -b BIN_ADMIN, --bin_admin=BIN_ADMIN
                        path to .../netbackup/bin/admincmd
  -s, --skip_bpgetconfig
                        Don't run bpgetconfig to confirm connection
  -n NUM_THREADS, --num_threads=NUM_THREADS
                        number of threads to run simultaneously
  -v, --verbose         print status messages to stdout
  -d, --debug           print debug messages to stdout
 </pre>
 
 ### Notes
 
<p>When using <code>skip_bpgetconfig</code> report will show this check as success</p>


## Use Case - Catalog Migration Pre-check
### Scenario

NetBackup on master server **nbumas01** needs to be migration to different server while keeping the 
same name. Target system has temporary name **nbutgt**.
  
### Solution

1. Create list of all clients with 

    * Windows <code>FOR /F "tokens=3" %a IN ('bpplclients -allunique') DO (echo %a) >> clients.txt</code>
  
    * Linux and *nix <code> bpplclients -allunique| awk '{print $3}' > clients.txt </code>

2. Verify client connectivity from the source system with [chk_con_nbu](#chk_con_nbu).

3.  Add temporary **nbutgt** name to all clients in source domain with [add_server_nbu](#add_server_nbu) 
or <code>add_media_server_on_clients</code>.

4. Verify client connectivity from the target system with [chk_con_nbu](#chk_con_nbu).

5. Delete temporary **nbutgt** name from all clients in source domain with [del_server_nbu](#del_server_nbu) 
or <code>add_media_server_on_clients</code>.

6. Crosscheck results from steps 1 and 4. Resolve connectivity issues.

# Reporting Tools

## bpdbjobs_delay_report

Takes ```bpdbjobs -all_columns``` output for the **bpbkar** and **bptm** delay messages and produces series of diagrams in one pdf file.

- Top ten clients by loss in throughput due to slow Clients/Network in MBps.

- Top ten clients  by loss in throughput due to slow Media server in MBps.

- Storage units (STU) report showing:
    - Total throughput in MBps.
    - Loss in throughput due to slow Clients/Network in MBps. 
    - Loss in throughput due to Media server storage performance in MBps. 
    
Formula is throughput is `total throughput * (time spend waiting for buffers/ total time)`

### Installation

Download windows release form the link on the the page. Otherwise install Python 3.4 or above and run 
```
git clone https://github.com/StoneRam/nbu_tools
pip install -r requirements_bpdbjobs.txt
python bpdbjobs_delay_report.py [...options]
```

###Usage
```
usage: bpdbjobs_delay_report [-h] -f|--file BPDBJOBS -o|--output OUTPUT
                      [-i|--interval INTERVAL] [-s|--start_date START_DATE]
                      [-n|--skip_slps] [-y|--only_slps]
                      [-t|--top_clients TOP_CLIENTS] [-e|--end_date END_DATE]

optional arguments:
  -h, --help            show this help message and exit
  -f|--file BPDBJOBS    file with bpdbjobs -all_columns output
  -o|--output OUTPUT    output pdf
  -i|--interval INTERVAL
                        Interval
  -s|--start_date START_DATE
                        The Start Date - format YYYY-MM-DD-HH24
  -n|--skip_slps        Don't count SLP stats
  -y|--only_slps        Only count SLP stats
  -t|--top_clients TOP_CLIENTS
                        Number of most delayed clients to display
  -e|--end_date END_DATE
                        The End Date - format YYYY-MM-DD-HH24

```

### Theory

Delay messages indicate two different issues:
 - Network/client performance is suspect in case of **bptm**
  `'waiting for full buffer'` messages. Buffers are available for 
writing on the media server, but client doesn't fill them in time.
 
- Media server performance issue in case of **bpbkar** messages `'waiting for empty buffer'`.
Client is sending data faster then media server is able to write it.

Some amount of delays expected and doesn't indicate any issues.

### Notes
- X-axis is labeled with Month-Day-24Hours format
- Time frame choosen based on minimun and  maximum value of jobs start and end time 
in `bpdbjobs` output. 
- Compiled version take longer to execute due to exe compression.

### Example reports

#### Clients

![Client report](https://github.com/StoneRam/nbu_tools/raw/master/images/client_example.png "Client report sample")

#### Media Server - STU

![Client report](https://github.com/StoneRam/nbu_tools/raw/master/images/stu_example.png "Client report sample")

## Use Case - Tune NetBackup
 

- For slow clients\network delays:

    - Increase\Enable multiplexing\number of streams on storage. So more clients will could storage buffers.
    - Increase number of data streams for client, i.e. **NEW_STREAM** directive in filesystem backup selections
    - Reduce size of Network buffers and increase size of Disk/Tape buffers.
    
  
- For media server delays:

    - Reduce number of streams on storage. Clients are racing for buffers reducing 
        overall performance.
    - Reduce size of Disk/Tape buffers and increase size of Network buffers
    - Spread backup schedules so they would overlap less, use generated report to make a judgement.
    
Often best solution is to resolve core issue, network bottleneck, underlying storage performance, etc.