# nbu_tools
Various tools for managing NetBackup

- [add_server_nbu](#add_server_nbu)

- [del_server_nbu](#del_server_nbu)

- [chk_con_nbu](#chk_con_nbu)

Use Case:
- [Use Case - Catalog Migration Pre-check][]

## add_server_nbu

<p>Adds SERVER entries to configuration, similar to bundled NetBackup's 
<code>add_media_server_on_clients</code>, but more flexible and faster.</p>
<p> Issue with <code>add_media_server_on_clients</code> that is runs in single thread and if there are 
multiple unreachable clients in the domain it takes very long time to complete. And server 
list is taken from bp.conf/registry on the master server, which might be undesirable in testing
or migration scenarios. </p>

Script is written for python 2.6.9 using only standard libraries. Compatible python interpreter 
is shipped with most major platforms. For convenience it was packaged with PyInstaller for 
Windows and Linux platforms.

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
Deletes SERVER entries to configuration. Very similar to [add_server_nbu](#add_server_nbu)
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


1. Verify client connectivity from the source system with [chk_con_nbu](#chk_con_nbu) or 
<code>bptestnetconn</code>.

2.  Add temporary **nbutgt** name to all clients in source domain with [add_server_nbu](#add_server_nbu) 
or <code>add_media_server_on_clients</code>.

3. Verify client connectivity from the target system with [chk_con_nbu](#chk_con_nbu).

4. Delete temporary **nbutgt** name from all clients in source domain with [del_server_nbu](#del_server_nbu) 
or <code>add_media_server_on_clients</code>.

5. Crosscheck results from steps 1 and 4. Resolve connectivity issues.
