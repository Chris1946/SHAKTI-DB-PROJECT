"""
PulseTrace — Developer Mode Insights

Technical, developer-focused data for every OS subsystem node.
Provides syscall signatures, debugging commands, performance counters,
and bottleneck patterns that software engineers need during analysis.

This module is pure data — no UI, no side effects.
"""

DEV_INSIGHTS = {
    "app": {
        "title": "User Application — Developer View",
        "key_syscalls": [
            ("read(fd, buf, count)", "Read from a file descriptor"),
            ("write(fd, buf, count)", "Write to a file descriptor"),
            ("open(path, flags, mode)", "Open a file or device"),
            ("close(fd)", "Close a file descriptor"),
            ("mmap(addr, len, prot, flags, fd, off)", "Map memory"),
            ("fork()", "Create a child process"),
            ("execve(path, argv, envp)", "Execute a program"),
            ("exit_group(status)", "Terminate all threads"),
        ],
        "perf_counters": [
            "task-clock — CPU time consumed",
            "context-switches — voluntary + involuntary",
            "page-faults — minor + major",
            "cpu-cycles — total cycles consumed",
            "instructions — total instructions retired",
            "cache-misses — LLC cache misses",
        ],
        "debug_commands": [
            "strace -f -c -p <PID>  — Summarize syscalls by frequency",
            "strace -f -e trace=file -p <PID>  — Trace only file operations",
            "perf stat -p <PID>  — Show performance counter summary",
            "perf record -g -p <PID>  — Record call-graph profile",
            "lsof -p <PID>  — List all open file descriptors",
            "pmap -x <PID>  — Detailed memory map",
        ],
        "bottleneck_patterns": [
            ("High syscall rate", "Use strace -c to find the most frequent calls. Buffer I/O or use io_uring."),
            ("GIL contention (Python)", "Use multiprocessing instead of threading for CPU work."),
            ("Memory leak", "Monitor RSS growth over time with ps or /proc/PID/status. Use valgrind or tracemalloc."),
            ("Excessive context switches", "Check voluntary vs involuntary with pidstat -w. Reduce lock contention."),
        ],
    },

    "container": {
        "title": "Container Runtime — Developer View",
        "key_syscalls": [
            ("clone(flags)", "Create process with namespace isolation"),
            ("unshare(flags)", "Disassociate from shared namespaces"),
            ("setns(fd, nstype)", "Join an existing namespace"),
            ("pivot_root(new, old)", "Change the root filesystem"),
            ("mount(src, target, fstype, flags, data)", "Mount filesystem"),
        ],
        "perf_counters": [
            "cgroup/cpu.stat — CPU usage within cgroup",
            "cgroup/memory.current — Current memory usage",
            "cgroup/io.stat — I/O bytes read/written per device",
        ],
        "debug_commands": [
            "docker stats <ID>  — Live resource usage",
            "docker top <ID>  — Processes inside container",
            "nsenter -t <PID> -m -p -n  — Enter container namespaces",
            "cat /sys/fs/cgroup/*/memory.max  — Memory limit",
            "cat /proc/<PID>/cgroup  — Show cgroup membership",
            "systemd-cgls  — Show cgroup hierarchy tree",
        ],
        "bottleneck_patterns": [
            ("CPU throttling", "Check cpu.stat for nr_throttled. Increase cpu.max or remove limit."),
            ("Memory OOM", "Check memory.events for oom_kill count. Increase memory.max."),
            ("Overlay I/O overhead", "Use named volumes for write-heavy paths instead of overlay."),
            ("Network latency", "Bridge overhead adds ~5-10μs. Use host networking for latency-sensitive apps."),
        ],
    },

    "database": {
        "title": "Database Engine — Developer View",
        "key_syscalls": [
            ("fdatasync(fd)", "Sync data (not metadata) to disk — WAL commit"),
            ("pread64(fd, buf, count, offset)", "Positional read — data page fetch"),
            ("pwrite64(fd, buf, count, offset)", "Positional write — data page flush"),
            ("shmget(key, size, flags)", "Allocate shared memory segment"),
            ("semop(semid, ops, nops)", "Semaphore operation for locking"),
            ("futex(addr, op, val)", "Fast user-space mutex"),
        ],
        "perf_counters": [
            "block:block_rq_issue — Block I/O requests issued",
            "syscalls:sys_enter_fdatasync — WAL sync frequency",
            "sched:sched_switch — Context switches (lock contention indicator)",
        ],
        "debug_commands": [
            "pg_stat_activity  — Active queries and their state",
            "EXPLAIN (ANALYZE, BUFFERS) <query>  — Query plan with I/O stats",
            "pg_stat_bgwriter  — Background writer statistics",
            "SELECT * FROM pg_locks WHERE NOT granted  — Blocked locks",
            "iostat -x 1  — Storage device utilization and latency",
            "bpftrace -e 'tracepoint:syscalls:sys_enter_fdatasync { @[comm] = count(); }'",
        ],
        "bottleneck_patterns": [
            ("Slow queries", "Run EXPLAIN ANALYZE. Add indexes, rewrite joins, use materialized views."),
            ("WAL sync latency", "Monitor fdatasync latency with biolatency. Consider faster storage."),
            ("Lock contention", "Check pg_locks for blocked queries. Reduce transaction duration."),
            ("Connection exhaustion", "Use pgbouncer connection pooling. Set max_connections appropriately."),
            ("Checkpoint storms", "Increase checkpoint_completion_target. Use bigger WAL buffers."),
        ],
    },

    "syscall": {
        "title": "System Call Interface — Developer View",
        "key_syscalls": [
            ("(architecture-specific entry point)", "SYSCALL instruction on x86-64"),
            ("copy_from_user(to, from, n)", "Safely copy data from user space"),
            ("copy_to_user(to, from, n)", "Safely copy data to user space"),
        ],
        "perf_counters": [
            "raw_syscalls:sys_enter — All syscall entries",
            "raw_syscalls:sys_exit — All syscall exits",
            "exceptions:page_fault_user — User-space page faults",
        ],
        "debug_commands": [
            "strace -c -p <PID>  — Syscall count and time summary",
            "strace -T -e trace=read,write -p <PID>  — Time each I/O syscall",
            "perf trace -p <PID>  — Low-overhead syscall tracing",
            "bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm, args[1]] = count(); }'",
            "ausyscall --dump  — List all syscall numbers",
            "seccomp-tools dump <binary>  — Show seccomp filters",
        ],
        "bottleneck_patterns": [
            ("Excessive syscalls", "Batch operations. Use sendmmsg/recvmmsg, writev/readv, io_uring."),
            ("Slow syscall", "Use strace -T to find which call takes longest. Often fdatasync or futex."),
            ("KPTI overhead", "Spectre mitigation adds ~5-10% to syscall cost. Check with nospectre_v2 kernel param."),
            ("Blocking calls in async code", "epoll_wait should not block. Check for accidental blocking I/O."),
        ],
    },

    "scheduler": {
        "title": "Process Scheduler — Developer View",
        "key_syscalls": [
            ("sched_yield()", "Voluntarily yield the CPU"),
            ("sched_setaffinity(pid, mask)", "Set CPU affinity mask"),
            ("sched_setscheduler(pid, policy, param)", "Set scheduling policy"),
            ("sched_getattr(pid, attr, size, flags)", "Get scheduling attributes"),
        ],
        "perf_counters": [
            "sched:sched_switch — Context switch events",
            "sched:sched_wakeup — Task wakeup events",
            "sched:sched_migrate_task — CPU migration events",
            "sched:sched_process_fork — Process fork events",
        ],
        "debug_commands": [
            "perf sched record -a  — Record scheduling events",
            "perf sched latency  — Show scheduling latency per task",
            "perf sched map  — Visual map of CPU usage over time",
            "pidstat -w 1  — Context switches per process",
            "mpstat -P ALL 1  — Per-CPU utilization",
            "cat /proc/<PID>/sched  — Detailed scheduler stats for a process",
        ],
        "bottleneck_patterns": [
            ("Runqueue saturation", "mpstat shows >100% util. Too many runnable threads. Reduce thread count."),
            ("CPU migration", "Frequent sched_migrate_task. Pin tasks with taskset/cpuset."),
            ("Priority inversion", "High-priority task blocked on lock held by low-priority. Use PI futexes."),
            ("Involuntary context switches", "Too many = high contention. pidstat -w reveals the culprit."),
        ],
    },

    "mmu": {
        "title": "Memory Management Unit — Developer View",
        "key_syscalls": [
            ("mmap(addr, len, prot, flags, fd, off)", "Create memory mapping"),
            ("munmap(addr, len)", "Remove memory mapping"),
            ("mprotect(addr, len, prot)", "Change memory protection"),
            ("madvise(addr, len, advice)", "Advise kernel on usage patterns"),
            ("brk(addr)", "Change data segment size (heap)"),
        ],
        "perf_counters": [
            "page-faults — Total page faults (minor + major)",
            "minor-faults — Pages resolved from cache",
            "major-faults — Pages loaded from disk/swap",
            "dTLB-load-misses — Data TLB misses",
            "iTLB-load-misses — Instruction TLB misses",
        ],
        "debug_commands": [
            "perf stat -e page-faults,dTLB-load-misses -p <PID>  — Page fault profile",
            "pmap -x <PID>  — Detailed virtual memory map",
            "cat /proc/<PID>/smaps_rollup  — Aggregated memory stats",
            "numastat -p <PID>  — NUMA memory allocation stats",
            "bpftrace -e 'software:major-faults:1 { @[comm] = count(); }'",
            "cat /proc/vmstat | grep -E 'pgfault|pgmajfault|thp'",
        ],
        "bottleneck_patterns": [
            ("Major page faults", "Pages loaded from disk. Increase RAM or reduce working set."),
            ("TLB misses", "Large working set. Use huge pages (madvise MADV_HUGEPAGE)."),
            ("Memory fragmentation", "Check /proc/buddyinfo. Compact with echo 1 > /proc/sys/vm/compact_memory."),
            ("NUMA remote access", "Check numastat. Bind process to local NUMA node."),
        ],
    },

    "vfs": {
        "title": "Virtual Filesystem — Developer View",
        "key_syscalls": [
            ("openat(dirfd, path, flags, mode)", "Open file relative to directory"),
            ("read(fd, buf, count) / pread64()", "Read from file"),
            ("write(fd, buf, count) / pwrite64()", "Write to file"),
            ("stat(path, statbuf) / fstat(fd, statbuf)", "Get file metadata"),
            ("unlink(path)", "Delete a file"),
            ("rename(old, new)", "Rename/move a file"),
        ],
        "perf_counters": [
            "ext4:ext4_da_write_begin — ext4 delayed allocation writes",
            "block:block_rq_issue — Block I/O requests to device",
            "filemap:mm_filemap_add_to_page_cache — Page cache additions",
        ],
        "debug_commands": [
            "strace -e trace=file -p <PID>  — Trace all file operations",
            "lsof -p <PID>  — List open files and their modes",
            "cat /proc/<PID>/fdinfo/<fd>  — Details of a specific fd",
            "fatrace  — Monitor filesystem-wide file access",
            "bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf(\"%s %s\\n\", comm, str(args->filename)); }'",
            "slabtop -o | grep dentry  — Dentry cache usage",
        ],
        "bottleneck_patterns": [
            ("Too many open files", "Check ulimit -n. Increase with ulimit -n 65536 or /etc/security/limits.conf."),
            ("Path lookup overhead", "Deep directories = more dentry lookups. Flatten paths."),
            ("Dentry cache pressure", "Monitor with slabtop. May need more RAM."),
            ("fsync latency", "Critical for databases. Monitor with biolatency. Use faster storage."),
        ],
    },

    "netstack": {
        "title": "TCP/IP Stack — Developer View",
        "key_syscalls": [
            ("socket(domain, type, protocol)", "Create a socket"),
            ("connect(fd, addr, len)", "Initiate a connection"),
            ("bind(fd, addr, len)", "Bind to an address"),
            ("listen(fd, backlog)", "Mark socket as passive"),
            ("accept4(fd, addr, len, flags)", "Accept a connection"),
            ("sendto(fd, buf, len, flags, addr, len)", "Send data"),
            ("recvfrom(fd, buf, len, flags, addr, len)", "Receive data"),
            ("setsockopt(fd, level, optname, optval, len)", "Set socket options"),
        ],
        "perf_counters": [
            "tcp:tcp_retransmit_skb — TCP retransmissions",
            "tcp:tcp_receive_reset — TCP RST received",
            "sock:sock_exceed_buf_limit — Socket buffer overflow",
            "net:net_dev_xmit — Packets transmitted",
        ],
        "debug_commands": [
            "ss -tnp  — Active TCP connections with process info",
            "ss -ti  — TCP internal state (cwnd, rtt, retrans)",
            "netstat -s | grep -i retrans  — Retransmission statistics",
            "tcpdump -i any -nn port 443  — Capture packets on port 443",
            "bpftrace -e 'tracepoint:tcp:tcp_retransmit_skb { @[comm] = count(); }'",
            "nstat -a  — Kernel network statistics (all counters)",
        ],
        "bottleneck_patterns": [
            ("TCP retransmissions", "Check ss -ti for retrans count. May indicate network loss or congestion."),
            ("Small socket buffers", "Increase net.core.rmem_max / wmem_max. Set SO_RCVBUF/SO_SNDBUF."),
            ("TIME_WAIT accumulation", "Enable net.ipv4.tcp_tw_reuse=1 for outbound connections."),
            ("Connection refused", "Server listen backlog too small. Increase somaxconn."),
        ],
    },

    "firewall": {
        "title": "Firewall (Netfilter) — Developer View",
        "key_syscalls": [
            ("setsockopt(SOL_IP, IPT_SO_SET_REPLACE)", "Load iptables rules"),
            ("getsockopt(SOL_IP, IPT_SO_GET_INFO)", "Get iptables info"),
        ],
        "perf_counters": [
            "nf_conntrack entries — /proc/sys/net/netfilter/nf_conntrack_count",
            "nf_conntrack max — /proc/sys/net/netfilter/nf_conntrack_max",
        ],
        "debug_commands": [
            "iptables -L -v -n  — List rules with packet/byte counters",
            "nft list ruleset  — Show all nftables rules",
            "conntrack -L  — List active connection tracking entries",
            "conntrack -C  — Count active connections",
            "conntrack -E  — Stream connection tracking events",
            "dmesg | grep nf_conntrack  — Check for table full warnings",
        ],
        "bottleneck_patterns": [
            ("Conntrack table full", "Increase nf_conntrack_max. Check conntrack -C."),
            ("Rule evaluation overhead", "Move most-matched rules first. Use ipsets for large lists."),
            ("NAT performance", "SNAT/DNAT has CPU cost. Consider DSR (Direct Server Return)."),
        ],
    },

    "cache": {
        "title": "Page Cache — Developer View",
        "key_syscalls": [
            ("posix_fadvise(fd, offset, len, advice)", "Advise kernel on access pattern"),
            ("readahead(fd, offset, count)", "Initiate file readahead"),
            ("mincore(addr, len, vec)", "Check if pages are in memory"),
            ("sync_file_range(fd, offset, nbytes, flags)", "Sync a file range"),
        ],
        "perf_counters": [
            "filemap:mm_filemap_add_to_page_cache — Cache insertions",
            "filemap:mm_filemap_delete_from_page_cache — Cache evictions",
            "writeback:writeback_dirty_page — Dirty page count",
        ],
        "debug_commands": [
            "free -h  — Overview of cache/buffer usage",
            "vmstat 1  — bi/bo columns show block I/O rate",
            "cachestat (BCC tool)  — Page cache hit/miss rate",
            "fincore <file>  — Check if specific file pages are cached",
            "cat /proc/meminfo | grep -E 'Cached|Dirty|Writeback'",
            "echo 3 > /proc/sys/vm/drop_caches  — Drop page cache (CAUTION)",
        ],
        "bottleneck_patterns": [
            ("Low cache hit rate", "Working set exceeds RAM. Add more memory or reduce working set."),
            ("Writeback storms", "Too many dirty pages. Reduce vm.dirty_ratio / vm.dirty_bytes."),
            ("Cache pollution", "Large sequential scans evicting useful cache. Use POSIX_FADV_DONTNEED."),
        ],
    },

    "iosched": {
        "title": "I/O Scheduler — Developer View",
        "key_syscalls": [
            ("ioprio_set(which, who, ioprio)", "Set I/O scheduling class and priority"),
            ("io_uring_setup(entries, params)", "Set up io_uring instance"),
            ("io_uring_enter(fd, to_submit, ...)", "Submit and wait for I/O"),
        ],
        "perf_counters": [
            "block:block_rq_issue — I/O requests sent to device",
            "block:block_rq_complete — I/O requests completed",
            "block:block_bio_queue — BIOs queued to scheduler",
        ],
        "debug_commands": [
            "iostat -x 1  — Extended I/O statistics per device",
            "cat /sys/block/*/queue/scheduler  — Current I/O scheduler",
            "blktrace -d /dev/sda -o - | blkparse -i -  — Live block trace",
            "bpftrace -e 'tracepoint:block:block_rq_complete { @us = hist(args->nr_sector); }'",
            "ionice -c 3 <command>  — Run with idle I/O priority",
            "biolatency (BCC tool)  — Block I/O latency histogram",
        ],
        "bottleneck_patterns": [
            ("High await", "iostat shows high await. Storage overloaded or queue too deep."),
            ("I/O starvation", "One process monopolizing I/O. Use ionice or BFQ scheduler."),
            ("Queue depth saturation", "nr_requests reached. Increase or optimize I/O pattern."),
        ],
    },

    "cpu": {
        "title": "CPU — Developer View",
        "key_syscalls": [
            ("sched_setaffinity(pid, mask)", "Pin to specific CPU cores"),
            ("perf_event_open(attr, pid, cpu, ...)", "Open performance counter"),
            ("clock_gettime(CLOCK_MONOTONIC, ts)", "High-precision timestamp"),
        ],
        "perf_counters": [
            "cpu-cycles — Total CPU cycles",
            "instructions — Instructions retired (IPC = instructions/cycles)",
            "cache-references — LLC cache accesses",
            "cache-misses — LLC cache misses",
            "branch-misses — Branch mispredictions",
            "L1-dcache-load-misses — L1 data cache misses",
        ],
        "debug_commands": [
            "perf stat -d -p <PID>  — Detailed CPU counter summary",
            "perf record -g -p <PID> && perf report  — Call-graph profiling",
            "perf top -p <PID>  — Live function-level profiling",
            "turbostat  — CPU frequency, power, and thermal monitoring",
            "lscpu  — CPU architecture details",
            "mpstat -P ALL 1  — Per-core utilization",
        ],
        "bottleneck_patterns": [
            ("Low IPC", "IPC < 1.0 usually means memory-bound. Check cache misses."),
            ("High branch misses", "> 5% miss rate. Restructure branches, use branchless code."),
            ("Thermal throttling", "turbostat shows frequency drops. Improve cooling."),
            ("False sharing", "Two cores writing adjacent variables in same cache line. Pad to 64 bytes."),
        ],
    },

    "gpu": {
        "title": "GPU — Developer View",
        "key_syscalls": [
            ("ioctl(fd, DRM_IOCTL_*)", "GPU command submission via DRM"),
            ("mmap()", "Map GPU buffers into user space"),
        ],
        "perf_counters": [
            "GPU utilization — nvidia-smi or intel_gpu_top",
            "VRAM usage — nvidia-smi --query-gpu=memory.used",
            "PCIe throughput — nvidia-smi dmon",
        ],
        "debug_commands": [
            "nvidia-smi  — NVIDIA GPU status (util, mem, temp, power)",
            "nvidia-smi dmon  — Live GPU monitoring (detailed)",
            "intel_gpu_top  — Intel GPU utilization",
            "radeontop  — AMD GPU utilization",
            "nvtop  — Interactive GPU process monitor",
            "nsys profile <command>  — NVIDIA Nsight Systems profiling",
        ],
        "bottleneck_patterns": [
            ("Low GPU utilization", "CPU bottleneck or excessive sync points. Overlap compute and transfer."),
            ("VRAM exhaustion", "Reduce batch size, use gradient checkpointing, or use model parallelism."),
            ("PCIe bottleneck", "Minimize host↔device transfers. Use pinned memory and async copies."),
        ],
    },

    "ram": {
        "title": "Physical RAM — Developer View",
        "key_syscalls": [
            ("mmap(MAP_ANONYMOUS)", "Allocate anonymous memory pages"),
            ("mbind(addr, len, mode, nodemask)", "Set NUMA memory policy"),
            ("get_mempolicy()", "Get current NUMA policy"),
        ],
        "perf_counters": [
            "mem_load_retired.l3_miss — LLC cache misses hitting DRAM",
            "node-load-misses — NUMA remote memory accesses",
        ],
        "debug_commands": [
            "free -h  — Memory usage overview",
            "cat /proc/meminfo  — Detailed kernel memory statistics",
            "cat /proc/buddyinfo  — Free page fragmentation",
            "slabtop  — Kernel slab allocator usage",
            "numastat -m  — NUMA memory allocation per node",
            "vmstat 1  — Memory activity (si/so = swap, bi/bo = block I/O)",
        ],
        "bottleneck_patterns": [
            ("OOM kills", "Check dmesg for 'Out of memory'. Set oom_score_adj or increase RAM."),
            ("NUMA imbalance", "Process memory on remote node. Use numactl --membind."),
            ("Memory fragmentation", "Large contiguous allocations failing. Use huge pages."),
        ],
    },

    "swap": {
        "title": "Swap Space — Developer View",
        "key_syscalls": [
            ("swapon(path, flags)", "Activate a swap area"),
            ("swapoff(path)", "Deactivate a swap area"),
        ],
        "perf_counters": [
            "pgpgin / pgpgout — Pages paged in/out (from /proc/vmstat)",
            "pswpin / pswpout — Pages swapped in/out (from /proc/vmstat)",
        ],
        "debug_commands": [
            "swapon --show  — List active swap areas",
            "vmstat 1  — si/so columns show swap in/out rate",
            "cat /proc/meminfo | grep Swap  — Swap usage",
            "cat /proc/sys/vm/swappiness  — Current swappiness value",
            "sar -W 1  — Swap activity over time",
            "bpftrace -e 'kprobe:swap_readpage { @[comm] = count(); }'",
        ],
        "bottleneck_patterns": [
            ("Swap thrashing", "High si/so in vmstat. Add RAM or reduce working set."),
            ("Slow swap device", "Use SSD or zram for swap. Never use network storage."),
        ],
    },

    "nic": {
        "title": "Network Interface — Developer View",
        "key_syscalls": [
            ("sendmsg(fd, msg, flags)", "Send via socket (user-level)"),
            ("recvmsg(fd, msg, flags)", "Receive via socket (user-level)"),
        ],
        "perf_counters": [
            "net:net_dev_xmit — Packets transmitted",
            "net:netif_receive_skb — Packets received",
            "NIC driver statistics — ethtool -S <iface>",
        ],
        "debug_commands": [
            "ethtool -S <iface>  — Driver-level NIC statistics",
            "ethtool -g <iface>  — Ring buffer sizes",
            "ethtool -k <iface>  — Offload features status",
            "ip -s link show <iface>  — Interface packet/byte counters",
            "cat /proc/interrupts | grep <iface>  — IRQ distribution",
            "cat /proc/net/softnet_stat  — Per-CPU packet processing stats",
        ],
        "bottleneck_patterns": [
            ("RX drops", "Ring buffer overflow. Increase with ethtool -G <iface> rx 4096."),
            ("IRQ imbalance", "One core saturated. Set smp_affinity or use irqbalance."),
            ("Softirq overhead", "ksoftirqd consuming CPU. Consider XDP or DPDK for bypass."),
        ],
    },

    "ssd": {
        "title": "NVMe/SSD Storage — Developer View",
        "key_syscalls": [
            ("io_submit(ctx, nr, iocbpp)", "Submit async I/O requests"),
            ("io_getevents(ctx, min, max, events, timeout)", "Wait for async I/O"),
            ("fallocate(fd, mode, offset, len)", "Preallocate file space"),
            ("ftruncate(fd, length)", "Truncate file to specified length"),
        ],
        "perf_counters": [
            "block:block_rq_complete — Completed I/O requests",
            "nvme:nvme_complete_rq — NVMe command completions",
        ],
        "debug_commands": [
            "iostat -x 1  — Per-device I/O stats (await, %util, IOPS)",
            "nvme smart-log /dev/nvme0  — SMART health + wear data",
            "fio --name=test --rw=randread --bs=4k --numjobs=4  — Benchmark IOPS",
            "blktrace -d /dev/nvme0n1 -o - | blkparse -i -  — Block trace",
            "biolatency (BCC tool)  — I/O latency distribution",
            "cat /sys/block/nvme0n1/queue/scheduler  — Current scheduler",
        ],
        "bottleneck_patterns": [
            ("High await", "I/O taking too long. Check queue depth and device health."),
            ("Write amplification", "SMART shows high write count vs host writes. More TRIM, less random writes."),
            ("Thermal throttling", "Check SMART temperature. Sustained writes can overheat."),
        ],
    },

    "dns": {
        "title": "DNS Resolver — Developer View",
        "key_syscalls": [
            ("sendto(fd, query, len, 0, dns_addr, addrlen)", "Send DNS query (UDP)"),
            ("recvfrom(fd, buf, len, 0, ...)", "Receive DNS response"),
        ],
        "perf_counters": [
            "DNS resolution time — measured at application level",
        ],
        "debug_commands": [
            "dig google.com  — Query DNS with detailed output",
            "dig +trace google.com  — Full recursive resolution path",
            "drill google.com  — DNS lookup (alternative to dig)",
            "resolvectl query google.com  — systemd-resolved query",
            "cat /etc/resolv.conf  — Configured DNS servers",
            "systemd-resolve --status  — DNS resolver status",
        ],
        "bottleneck_patterns": [
            ("Slow resolution", "Check /etc/resolv.conf for slow servers. Use local cache."),
            ("DNS timeout", "Default 5s timeout in glibc. Configure options timeout:1 in resolv.conf."),
        ],
    },

    "internet": {
        "title": "Internet / External Network — Developer View",
        "key_syscalls": [
            ("connect(fd, remote_addr, len)", "Establish connection to remote server"),
        ],
        "perf_counters": [
            "TCP RTT — ss -ti (rtt field)",
            "Packet loss — netstat -s (retransmits)",
        ],
        "debug_commands": [
            "mtr <host>  — Continuous traceroute with packet loss stats",
            "traceroute -T <host>  — TCP traceroute (bypasses ICMP blocks)",
            "curl -w '%{time_connect} %{time_starttransfer} %{time_total}' -o /dev/null <url>",
            "openssl s_client -connect host:443  — TLS handshake details",
            "ss -ti dst <ip>  — TCP internal state for remote connection",
            "ping -c 10 <host>  — Basic latency and loss measurement",
        ],
        "bottleneck_patterns": [
            ("High RTT", "Physical distance or congested path. Use CDN or edge computing."),
            ("Packet loss", "Network congestion or faulty link. Check mtr for the hop with loss."),
            ("TLS overhead", "Use TLS 1.3 with 0-RTT. Connection pooling reduces handshakes."),
        ],
    },
}


def get_developer_html(node_id: str, accent_color: str, text_color: str, muted_color: str) -> str:
    """Generate rich HTML content for Developer Mode inspector."""
    entry = DEV_INSIGHTS.get(node_id)
    if not entry:
        return f"<p style='color:{muted_color}'>No developer insights for '{node_id}'.</p>"

    html = f"<h3 style='color:{accent_color}; margin:0 0 8px 0;'>{entry['title']}</h3>"

    # Key syscalls
    html += f"<h4 style='color:{accent_color}; margin:10px 0 4px 0; font-size:12px;'>🔧 KEY SYSTEM CALLS</h4>"
    html += "<table style='border-collapse:collapse; width:100%;'>"
    for sig, desc in entry["key_syscalls"]:
        html += (
            f"<tr>"
            f"<td style='color:#34d399; font-family:monospace; font-size:10px; padding:2px 6px 2px 0; white-space:nowrap;'>{sig}</td>"
            f"<td style='color:{muted_color}; font-size:10px; padding:2px 0;'>{desc}</td>"
            f"</tr>"
        )
    html += "</table>"

    # Performance counters
    html += f"<h4 style='color:{accent_color}; margin:10px 0 4px 0; font-size:12px;'>📊 PERFORMANCE COUNTERS</h4>"
    html += "<ul style='margin:0; padding-left:16px;'>"
    for pc in entry["perf_counters"]:
        html += f"<li style='color:{text_color}; font-family:monospace; font-size:10px; margin:1px 0;'>{pc}</li>"
    html += "</ul>"

    # Debug commands
    html += f"<h4 style='color:{accent_color}; margin:10px 0 4px 0; font-size:12px;'>💻 DEBUGGING COMMANDS</h4>"
    for cmd in entry["debug_commands"]:
        html += (
            f"<div style='background:#1e293b; border:1px solid #334155; border-radius:3px; "
            f"padding:3px 6px; margin:2px 0; font-family:monospace; font-size:10px; color:#e2e8f0;'>"
            f"{cmd}</div>"
        )

    # Bottleneck patterns
    html += f"<h4 style='color:{accent_color}; margin:10px 0 4px 0; font-size:12px;'>⚠️ BOTTLENECK PATTERNS</h4>"
    for pattern, fix in entry["bottleneck_patterns"]:
        html += (
            f"<div style='margin:4px 0;'>"
            f"<span style='color:#fbbf24; font-size:11px; font-weight:bold;'>{pattern}</span><br/>"
            f"<span style='color:{muted_color}; font-size:10px;'>{fix}</span>"
            f"</div>"
        )

    return html
