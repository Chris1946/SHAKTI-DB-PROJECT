"""
PulseTrace — OS Subsystem Knowledge Base (Learning Mode)

Educational content for every node in the OS Digital Twin.
Each entry teaches developers what the subsystem does, how it interacts
with the kernel, common bottlenecks, and best practices.

This module is pure data — no UI, no side effects.
"""

KNOWLEDGE = {
    # ══════════════════════════════════════════════════════════════
    # COLUMN 1: USER APPLICATIONS
    # ══════════════════════════════════════════════════════════════

    "app": {
        "title": "User Application",
        "purpose": (
            "A user-space process running your code. It cannot directly access "
            "hardware — every I/O operation, memory allocation, or network call "
            "must pass through the kernel via system calls."
        ),
        "responsibilities": [
            "Execute application logic (business rules, UI, computation)",
            "Request OS services through the syscall interface",
            "Manage its own virtual address space",
            "Handle signals from the kernel (SIGTERM, SIGKILL, etc.)",
        ],
        "kernel_interaction": (
            "Every interaction with the outside world goes through the syscall "
            "interface. read(), write(), open(), socket(), mmap(), fork(), exec() — "
            "these are the gateways. The kernel validates every request, enforces "
            "permissions, and mediates access to shared resources."
        ),
        "common_bottlenecks": [
            "Excessive syscalls (e.g., reading files 1 byte at a time)",
            "GIL contention in CPython preventing true parallelism",
            "Memory leaks causing the OOM killer to intervene",
            "Blocking I/O in event loops starving other tasks",
            "CPU-bound loops without yielding (starving scheduler)",
        ],
        "related_concepts": [
            "Process vs Thread",
            "User space vs Kernel space",
            "Virtual memory and address spaces",
            "Signals and signal handlers",
            "Process lifecycle (fork/exec/wait/exit)",
        ],
        "best_practices": [
            "Use buffered I/O to minimize syscall overhead",
            "Prefer async I/O for network-bound applications",
            "Profile before optimizing — measure don't guess",
            "Handle signals gracefully for clean shutdown",
            "Set resource limits (ulimit) to prevent runaway processes",
        ],
        "documentation": [
            "man 2 syscalls — List of all Linux system calls",
            "man 7 signal — Signal handling overview",
            "proc(5) — The /proc filesystem for process introspection",
        ],
    },

    "container": {
        "title": "Container Runtime",
        "purpose": (
            "An isolated execution environment using Linux namespaces and cgroups. "
            "Containers share the host kernel but have their own view of the filesystem, "
            "network, PIDs, and resource limits."
        ),
        "responsibilities": [
            "Provide filesystem isolation (overlay/unionfs)",
            "Enforce resource limits via cgroups (CPU, memory, I/O)",
            "Isolate network via network namespaces",
            "Manage PID namespaces (PID 1 inside container)",
        ],
        "kernel_interaction": (
            "Containers are NOT virtual machines. They use clone() with namespace flags "
            "(CLONE_NEWNS, CLONE_NEWPID, CLONE_NEWNET) to create isolated views. "
            "Cgroups (/sys/fs/cgroup) enforce resource quotas. The kernel handles all "
            "isolation — containers are just cleverly sandboxed processes."
        ),
        "common_bottlenecks": [
            "Overlay filesystem overhead on write-heavy workloads",
            "CPU throttling when cgroup limits are too tight",
            "Network namespace overhead for high-throughput services",
            "PID exhaustion inside the container namespace",
            "Noisy neighbor effects when sharing host resources",
        ],
        "related_concepts": [
            "Linux Namespaces (mount, PID, network, user, IPC, UTS)",
            "Cgroups v1 vs v2",
            "Overlay filesystems (OverlayFS)",
            "Seccomp-bpf for syscall filtering",
            "Container networking (veth pairs, bridge, macvlan)",
        ],
        "best_practices": [
            "Set memory limits to prevent OOM on the host",
            "Use multi-stage builds to minimize image size",
            "Never run as root inside containers",
            "Use read-only root filesystems where possible",
            "Monitor cgroup metrics for throttling detection",
        ],
        "documentation": [
            "man 7 namespaces — Linux namespace overview",
            "man 7 cgroups — Control groups documentation",
            "Documentation/cgroup-v2.txt in the kernel source",
        ],
    },

    "database": {
        "title": "Database Engine",
        "purpose": (
            "A process that manages persistent structured data. Databases handle "
            "concurrency, transactions, indexing, and durability guarantees. They "
            "interact heavily with the filesystem, memory, and network subsystems."
        ),
        "responsibilities": [
            "Parse and optimize SQL/query language statements",
            "Manage buffer pools (caching data pages in RAM)",
            "Handle transactions (ACID guarantees)",
            "Write-ahead logging (WAL) for crash recovery",
            "Connection pooling and authentication",
        ],
        "kernel_interaction": (
            "Databases use mmap() or direct I/O for data files, fsync()/fdatasync() "
            "for durability, futex() for internal locking, and socket() for client "
            "connections. PostgreSQL uses shared memory (shmget/shmat) extensively. "
            "The buffer pool competes with the kernel's page cache for RAM."
        ),
        "common_bottlenecks": [
            "Slow queries (missing indexes, full table scans)",
            "WAL write latency (critical for commit performance)",
            "Lock contention on hot rows/tables",
            "Connection exhaustion (too many clients)",
            "Checkpoint storms (bulk dirty page flushes)",
        ],
        "related_concepts": [
            "B-tree and Hash indexes",
            "MVCC (Multi-Version Concurrency Control)",
            "Write-Ahead Logging",
            "Buffer pool and shared buffers",
            "Connection pooling (pgbouncer, pgpool)",
        ],
        "best_practices": [
            "Use EXPLAIN ANALYZE to understand query plans",
            "Size shared_buffers to ~25% of available RAM",
            "Use connection pooling to limit backend processes",
            "Monitor WAL lag and replication delay",
            "Regular VACUUM to prevent table bloat",
        ],
        "documentation": [
            "PostgreSQL docs: www.postgresql.org/docs/current/",
            "man 2 fsync — Synchronize file data to storage",
            "man 2 mmap — Memory-mapped file I/O",
        ],
    },

    # ══════════════════════════════════════════════════════════════
    # COLUMN 2: KERNEL SUBSYSTEMS
    # ══════════════════════════════════════════════════════════════

    "syscall": {
        "title": "System Call Interface",
        "purpose": (
            "The gateway between user space and kernel space. Every request your "
            "application makes to the OS — reading a file, sending a packet, "
            "allocating memory — crosses this boundary via a syscall."
        ),
        "responsibilities": [
            "Validate user-space arguments (prevent kernel corruption)",
            "Switch CPU from user mode (Ring 3) to kernel mode (Ring 0)",
            "Dispatch to the correct kernel handler function",
            "Copy results back to user space safely",
            "Handle signals pending after the syscall returns",
        ],
        "kernel_interaction": (
            "On x86-64, syscalls use the SYSCALL instruction which transfers control "
            "to the kernel entry point. The syscall number in RAX selects the handler "
            "from sys_call_table[]. Arguments are passed in RDI, RSI, RDX, R10, R8, R9. "
            "The kernel uses copy_from_user()/copy_to_user() to safely transfer data."
        ),
        "common_bottlenecks": [
            "Syscall overhead (~100ns each on modern CPUs)",
            "Excessive context switches between user/kernel mode",
            "Copying large buffers between user/kernel space",
            "Blocking syscalls stalling async event loops",
            "Spectre/Meltdown mitigations adding overhead (KPTI)",
        ],
        "related_concepts": [
            "CPU privilege rings (Ring 0 vs Ring 3)",
            "System call table (sys_call_table)",
            "vDSO (virtual dynamic shared object) for fast calls",
            "io_uring — batch syscall submission",
            "seccomp-bpf — syscall filtering",
        ],
        "best_practices": [
            "Batch I/O operations to reduce syscall count",
            "Use io_uring for high-throughput I/O",
            "Use vDSO calls (gettimeofday) instead of real syscalls",
            "Profile with strace -c to count syscalls per type",
            "Avoid mixing blocking and non-blocking I/O patterns",
        ],
        "documentation": [
            "man 2 syscall — Indirect system call",
            "man 2 syscalls — Complete list of system calls",
            "man 7 vdso — Virtual dynamic shared object",
        ],
    },

    "scheduler": {
        "title": "Process Scheduler",
        "purpose": (
            "Decides which thread runs on which CPU core and for how long. "
            "The scheduler is the heartbeat of the OS — it multiplexes many "
            "threads onto a limited number of CPU cores."
        ),
        "responsibilities": [
            "Select the next task to run on each CPU (pick_next_task)",
            "Handle preemption when a higher-priority task arrives",
            "Balance load across CPU cores (load balancer)",
            "Manage scheduling classes (CFS, RT, deadline, idle)",
            "Handle CPU affinity and NUMA-aware scheduling",
        ],
        "kernel_interaction": (
            "Linux uses the Completely Fair Scheduler (CFS) with a red-black tree "
            "of runnable tasks sorted by virtual runtime. Since kernel 6.6, the "
            "EEVDF scheduler replaces CFS for better latency. schedule() is called "
            "on every timer tick, syscall return, and voluntary yield."
        ),
        "common_bottlenecks": [
            "Runqueue saturation (too many runnable threads per core)",
            "Priority inversion (low-priority task holding a lock)",
            "CPU migration overhead (task bouncing between cores)",
            "NUMA cross-node scheduling (remote memory access penalty)",
            "Real-time tasks starving batch tasks",
        ],
        "related_concepts": [
            "CFS (Completely Fair Scheduler)",
            "EEVDF (Earliest Eligible Virtual Deadline First)",
            "Scheduling classes (SCHED_OTHER, SCHED_FIFO, SCHED_DEADLINE)",
            "Nice values and priorities",
            "CPU affinity (sched_setaffinity)",
        ],
        "best_practices": [
            "Use taskset/cpuset to pin latency-sensitive tasks",
            "Monitor /proc/schedstat for scheduler statistics",
            "Avoid over-threading (threads > cores = contention)",
            "Use cgroups to isolate workload scheduling",
            "Use perf sched for detailed scheduler analysis",
        ],
        "documentation": [
            "Documentation/scheduler/ in the kernel source",
            "man 7 sched — Scheduling overview",
            "man 2 sched_setaffinity — Set CPU affinity",
        ],
    },

    "mmu": {
        "title": "Memory Management Unit",
        "purpose": (
            "Translates virtual addresses (what your program sees) to physical "
            "addresses (actual RAM locations). The MMU enforces memory protection "
            "and enables each process to have its own private address space."
        ),
        "responsibilities": [
            "Translate virtual → physical addresses via page tables",
            "Enforce memory permissions (read/write/execute)",
            "Handle page faults (demand paging, copy-on-write)",
            "Manage TLB (Translation Lookaside Buffer) entries",
            "Support huge pages (2MB, 1GB) for reduced TLB pressure",
        ],
        "kernel_interaction": (
            "The kernel maintains 4-level page tables (PGD→PUD→PMD→PTE) for each "
            "process. On a page fault, the kernel's do_page_fault() handler decides: "
            "allocate a new page, load from swap, trigger copy-on-write, or send "
            "SIGSEGV. mmap() creates new virtual mappings, munmap() releases them."
        ),
        "common_bottlenecks": [
            "TLB misses (especially with large working sets)",
            "Page fault storms during process startup",
            "Swap thrashing (constant page-in/page-out)",
            "NUMA remote memory access latency",
            "Transparent Huge Page (THP) compaction stalls",
        ],
        "related_concepts": [
            "Page tables (4-level on x86-64)",
            "TLB (Translation Lookaside Buffer)",
            "Demand paging and copy-on-write",
            "Huge pages (hugetlbfs, THP)",
            "NUMA (Non-Uniform Memory Access)",
        ],
        "best_practices": [
            "Use huge pages for large, stable allocations",
            "Monitor /proc/vmstat for page fault rates",
            "Pin NUMA-sensitive workloads to local nodes",
            "Use madvise() to hint the kernel about access patterns",
            "Watch for THP compaction via /proc/vmstat",
        ],
        "documentation": [
            "Documentation/mm/ in the kernel source",
            "man 2 mmap — Map files or devices into memory",
            "man 2 madvise — Give advice about memory usage",
        ],
    },

    "vfs": {
        "title": "Virtual Filesystem (VFS)",
        "purpose": (
            "A unified abstraction layer that lets applications use the same "
            "API (open/read/write/close) regardless of the underlying filesystem "
            "(ext4, XFS, APFS, NFS, procfs, etc.)."
        ),
        "responsibilities": [
            "Route file operations to the correct filesystem driver",
            "Manage the dentry cache (directory entry lookups)",
            "Maintain the inode cache (file metadata)",
            "Handle file descriptors and the open file table",
            "Implement the mount system and mount namespaces",
        ],
        "kernel_interaction": (
            "VFS defines struct file_operations — every filesystem implements this "
            "interface. When you call open(), the kernel walks the dentry cache, "
            "finds the inode, creates a struct file, and returns an fd. Subsequent "
            "read()/write() calls dispatch through the filesystem's operations table."
        ),
        "common_bottlenecks": [
            "Dentry cache misses (cold directory lookups)",
            "Inode exhaustion (too many small files)",
            "File descriptor limits (ulimit -n)",
            "Lock contention on directory operations",
            "Path resolution overhead (deep directory trees)",
        ],
        "related_concepts": [
            "Inodes and dentries",
            "File descriptors and open file table",
            "Filesystem types (ext4, XFS, btrfs, APFS)",
            "Special filesystems (procfs, sysfs, devfs)",
            "Mount namespaces",
        ],
        "best_practices": [
            "Increase inotify watches for file-watching apps",
            "Use O_DIRECT for database-like direct I/O",
            "Monitor dentry/inode cache with slabtop",
            "Avoid deep directory nesting (path lookup overhead)",
            "Use fstat() instead of stat() when you have an open fd",
        ],
        "documentation": [
            "Documentation/filesystems/vfs.rst in the kernel source",
            "man 2 open — Open and possibly create a file",
            "man 7 path_resolution — How pathnames are resolved",
        ],
    },

    "netstack": {
        "title": "TCP/IP Network Stack",
        "purpose": (
            "Implements the full network protocol stack: Ethernet, IP, TCP, UDP, "
            "and higher-level protocols. Handles routing, congestion control, "
            "packet segmentation, and connection management."
        ),
        "responsibilities": [
            "Manage TCP connections (3-way handshake, FIN/RST)",
            "Implement congestion control (Cubic, BBR, DCTCP)",
            "Fragment and reassemble IP packets",
            "Route packets to the correct interface",
            "Handle socket buffers (sk_buff) and queuing",
        ],
        "kernel_interaction": (
            "The kernel's net/ subsystem processes packets through a layered stack. "
            "Incoming: NIC → NAPI → netfilter → routing → socket buffer → application. "
            "Outgoing: socket → routing → netfilter → qdisc → NIC driver → wire. "
            "Each layer can modify, drop, or queue the packet."
        ),
        "common_bottlenecks": [
            "Small socket buffer sizes (rmem/wmem limits)",
            "TCP retransmissions (packet loss, congestion)",
            "Connection table exhaustion (too many TIME_WAIT)",
            "Receive buffer overflow (net.core.rmem_max)",
            "IRQ affinity imbalance (one core handling all NIC interrupts)",
        ],
        "related_concepts": [
            "TCP congestion control (Cubic vs BBR)",
            "Socket buffers (sk_buff)",
            "Netfilter and iptables/nftables",
            "Traffic control (tc) and queueing disciplines",
            "XDP (eXpress Data Path) for kernel-bypass",
        ],
        "best_practices": [
            "Tune net.core.rmem_max and wmem_max for throughput",
            "Use BBR congestion control for WAN traffic",
            "Enable TCP_NODELAY for latency-sensitive apps",
            "Monitor retransmits with ss -ti",
            "Use SO_REUSEPORT for multi-threaded servers",
        ],
        "documentation": [
            "Documentation/networking/ in the kernel source",
            "man 7 tcp — TCP protocol implementation",
            "man 7 socket — Socket interface overview",
        ],
    },

    "firewall": {
        "title": "Firewall (Netfilter)",
        "purpose": (
            "Inspects, filters, and modifies network packets as they traverse "
            "the kernel's network stack. Implements firewalling, NAT, port "
            "forwarding, and packet mangling."
        ),
        "responsibilities": [
            "Apply iptables/nftables rules to packets",
            "Perform Network Address Translation (SNAT/DNAT)",
            "Track connection state (conntrack)",
            "Rate-limit or drop malicious traffic",
            "Log matched packets for auditing",
        ],
        "kernel_interaction": (
            "Netfilter hooks into 5 points in the packet path: PREROUTING, INPUT, "
            "FORWARD, OUTPUT, POSTROUTING. Each hook evaluates rules in order. "
            "conntrack maintains a hash table of active connections. nftables "
            "compiles rules to a bytecode VM for faster evaluation."
        ),
        "common_bottlenecks": [
            "Large rule sets (linear scan in iptables)",
            "Conntrack table exhaustion (nf_conntrack_max)",
            "NAT overhead on high-throughput services",
            "Stateful inspection CPU cost",
            "Logging overhead from verbose rules",
        ],
        "related_concepts": [
            "iptables vs nftables",
            "Connection tracking (conntrack)",
            "NAT (SNAT, DNAT, masquerade)",
            "Netfilter hooks and chains",
            "BPF-based packet filtering (XDP)",
        ],
        "best_practices": [
            "Use nftables instead of iptables for new setups",
            "Monitor conntrack usage: conntrack -C",
            "Increase nf_conntrack_max for busy servers",
            "Place most-matched rules first for performance",
            "Use ipsets for large IP lists instead of individual rules",
        ],
        "documentation": [
            "man 8 iptables — IPv4 packet filter administration",
            "man 8 nft — nftables framework",
            "Documentation/networking/nf_conntrack-sysctl.txt",
        ],
    },

    "cache": {
        "title": "Page Cache",
        "purpose": (
            "The kernel's in-memory cache of file data. When you read a file, "
            "the data is cached in RAM so subsequent reads are served from "
            "memory instead of hitting the slow storage device."
        ),
        "responsibilities": [
            "Cache recently read file pages in RAM",
            "Serve reads from cache when possible (cache hit)",
            "Write dirty pages back to disk (writeback)",
            "Evict cold pages when memory pressure rises",
            "Support memory-mapped file I/O (mmap)",
        ],
        "kernel_interaction": (
            "The page cache uses the radix tree (xarray since 5.x) to index cached "
            "pages by (inode, offset). read() first checks the cache via "
            "find_get_page(). On miss, it allocates a page and issues a bio to the "
            "block layer. Dirty pages are written back by the pdflush/flusher threads."
        ),
        "common_bottlenecks": [
            "Cache thrashing (working set > available RAM)",
            "Writeback storms (too many dirty pages flushed at once)",
            "Direct I/O bypassing cache (intentional but costs reads)",
            "Memory pressure causing premature eviction",
            "Readahead misconfiguration for sequential workloads",
        ],
        "related_concepts": [
            "Page cache vs buffer cache (unified since 2.4)",
            "Readahead (prefetching sequential file data)",
            "Dirty page writeback (vm.dirty_ratio)",
            "Drop caches: echo 3 > /proc/sys/vm/drop_caches",
            "Memory-mapped I/O (mmap)",
        ],
        "best_practices": [
            "Monitor cache hit rate with cachestat (BCC tool)",
            "Tune vm.dirty_ratio for write-heavy workloads",
            "Use fadvise(POSIX_FADV_SEQUENTIAL) for streaming reads",
            "Use O_DIRECT only when you manage your own cache",
            "Leave ~40-60% of RAM free for page cache",
        ],
        "documentation": [
            "Documentation/filesystems/vfs.rst (page cache section)",
            "man 2 posix_fadvise — File access pattern advice",
            "man 2 mincore — Check if pages are in memory",
        ],
    },

    "iosched": {
        "title": "I/O Scheduler",
        "purpose": (
            "Reorders and merges block I/O requests before sending them to the "
            "storage device. Optimizes throughput by reducing seek time on HDDs "
            "and batching requests for SSDs."
        ),
        "responsibilities": [
            "Merge adjacent I/O requests (bio merging)",
            "Prioritize reads over writes (or vice versa)",
            "Enforce I/O fairness between processes",
            "Support I/O priorities (ionice)",
            "Batch and order requests for device efficiency",
        ],
        "kernel_interaction": (
            "The block layer converts file operations into struct bio requests. "
            "The I/O scheduler (mq-deadline, BFQ, kyber, or none) reorders these "
            "before submitting to the device driver. Modern NVMe SSDs often use "
            "'none' scheduler since the device has its own internal queue."
        ),
        "common_bottlenecks": [
            "I/O queue depth saturation (nr_requests)",
            "Write starvation under heavy read workloads",
            "I/O priority inversion (background tasks blocking foreground)",
            "Scheduler overhead on fast NVMe devices",
            "BFQ overhead for high-IOPS workloads",
        ],
        "related_concepts": [
            "Block I/O layer (bio, request)",
            "Schedulers: mq-deadline, BFQ, kyber, none",
            "I/O priorities (ionice, ioprio_set)",
            "Multi-queue block layer (blk-mq)",
            "NVMe command queues",
        ],
        "best_practices": [
            "Use 'none' scheduler for NVMe SSDs",
            "Use BFQ for desktop responsiveness with HDDs",
            "Use ionice to deprioritize background I/O",
            "Monitor I/O latency with blktrace/bpftrace",
            "Check queue depth with /sys/block/*/queue/nr_requests",
        ],
        "documentation": [
            "Documentation/block/ in the kernel source",
            "man 1 ionice — Set or get I/O scheduling class and priority",
            "man 8 blktrace — Block layer I/O tracing",
        ],
    },

    # ══════════════════════════════════════════════════════════════
    # COLUMN 3: HARDWARE
    # ══════════════════════════════════════════════════════════════

    "cpu": {
        "title": "Central Processing Unit",
        "purpose": (
            "Executes machine instructions. Modern CPUs have multiple cores, "
            "deep pipelines, out-of-order execution, and multiple cache levels. "
            "Understanding CPU behavior is key to performance optimization."
        ),
        "responsibilities": [
            "Fetch, decode, and execute instructions",
            "Manage L1/L2/L3 caches for fast memory access",
            "Handle interrupts and exceptions",
            "Support hardware virtualization (VT-x, AMD-V)",
            "Enforce memory ordering and cache coherency",
        ],
        "kernel_interaction": (
            "The kernel manages CPU resources via the scheduler. It handles "
            "interrupts (IDT), manages per-CPU data structures, configures "
            "performance counters (PMU), and uses CPU features like TSC for "
            "timekeeping. The kernel's CPUID detection sets available features."
        ),
        "common_bottlenecks": [
            "Cache misses (L1/L2/L3 — increasingly expensive)",
            "Branch mispredictions (pipeline flush penalty)",
            "Thermal throttling reducing clock speed",
            "False sharing (different cores fighting over same cache line)",
            "Hyper-threading contention on shared execution units",
        ],
        "related_concepts": [
            "Instruction pipeline and out-of-order execution",
            "Cache hierarchy (L1d, L1i, L2, L3, LLC)",
            "Branch prediction and speculative execution",
            "SIMD (SSE, AVX, NEON) for parallel data processing",
            "Performance counters (PMU, perf_event)",
        ],
        "best_practices": [
            "Profile with perf stat for cache miss / branch mispredict rates",
            "Align hot data structures to cache line boundaries (64 bytes)",
            "Avoid false sharing with __cacheline_aligned padding",
            "Use perf record + perf report for hot-spot analysis",
            "Monitor thermal throttling with sensors/turbostat",
        ],
        "documentation": [
            "Intel® 64 and IA-32 Architectures Software Developer's Manuals",
            "man 1 perf — Performance analysis tools for Linux",
            "man 2 perf_event_open — Performance monitoring",
        ],
    },

    "gpu": {
        "title": "Graphics Processing Unit",
        "purpose": (
            "A massively parallel processor optimized for throughput-oriented "
            "workloads: rendering, ML inference, scientific simulation. GPUs have "
            "thousands of cores but each is simpler than a CPU core."
        ),
        "responsibilities": [
            "Execute graphics shaders and compute kernels",
            "Manage GPU memory (VRAM) and DMA transfers",
            "Handle display output and compositing",
            "Accelerate ML workloads (tensor operations)",
            "Video encode/decode (hardware codecs)",
        ],
        "kernel_interaction": (
            "The kernel's DRM (Direct Rendering Manager) subsystem manages GPU "
            "access. Applications use ioctl() on /dev/dri/* to submit command "
            "buffers. The kernel schedules GPU work, manages VRAM via TTM/GEM, "
            "and handles GPU fault recovery."
        ),
        "common_bottlenecks": [
            "PCIe bandwidth saturation (CPU↔GPU transfers)",
            "VRAM exhaustion (out-of-memory on GPU)",
            "Kernel launch overhead (too many small dispatches)",
            "Memory copy overhead (host↔device transfers)",
            "GPU compute / rendering contention",
        ],
        "related_concepts": [
            "DRM/KMS (Direct Rendering Manager / Kernel Mode Setting)",
            "Vulkan, OpenGL, CUDA, ROCm APIs",
            "GPU memory management (GEM, TTM)",
            "PCIe and NVLink interconnects",
            "Unified memory vs explicit memory management",
        ],
        "best_practices": [
            "Minimize host↔device memory copies",
            "Use pinned memory for faster DMA transfers",
            "Batch small operations into larger kernel launches",
            "Monitor GPU utilization with nvidia-smi or radeontop",
            "Use async compute for overlapping transfers and compute",
        ],
        "documentation": [
            "Documentation/gpu/ in the kernel source",
            "NVIDIA CUDA Programming Guide",
            "Vulkan specification (khronos.org)",
        ],
    },

    "ram": {
        "title": "Physical RAM",
        "purpose": (
            "Volatile main memory. All running processes, the kernel itself, "
            "page cache, and kernel buffers live in RAM. It's fast (~100ns latency) "
            "but limited and volatile (lost on power off)."
        ),
        "responsibilities": [
            "Store running process pages (code, data, heap, stack)",
            "Host the kernel's page cache for file I/O",
            "Provide memory for kernel data structures (slab allocator)",
            "Support DMA for device I/O (DMA zones)",
            "NUMA topology: local vs remote memory access",
        ],
        "kernel_interaction": (
            "The kernel's buddy allocator manages free physical pages in power-of-2 "
            "blocks. The slab allocator (SLUB) provides efficient small-object "
            "allocation. The kernel tracks memory zones (DMA, DMA32, Normal, HighMem) "
            "and NUMA nodes. /proc/meminfo shows the full picture."
        ),
        "common_bottlenecks": [
            "Memory exhaustion triggering the OOM killer",
            "NUMA remote access latency (2-3x slower than local)",
            "Memory fragmentation preventing huge page allocation",
            "Slab cache growth consuming available memory",
            "Memory bandwidth saturation on multi-core workloads",
        ],
        "related_concepts": [
            "Buddy allocator (free page management)",
            "Slab allocator (SLUB, small object caching)",
            "NUMA (Non-Uniform Memory Access)",
            "Memory zones (DMA, Normal, HighMem)",
            "OOM killer and oom_score_adj",
        ],
        "best_practices": [
            "Monitor /proc/meminfo and /proc/buddyinfo",
            "Use numactl to bind processes to NUMA nodes",
            "Set vm.overcommit_memory appropriately",
            "Watch for slab growth with slabtop",
            "Use cgroups to limit per-container memory",
        ],
        "documentation": [
            "Documentation/mm/ in the kernel source",
            "man 5 proc — /proc/meminfo documentation",
            "man 8 numactl — NUMA policy control",
        ],
    },

    "swap": {
        "title": "Swap Space",
        "purpose": (
            "Extends available memory by using disk as overflow. When RAM is full, "
            "the kernel moves least-recently-used pages to swap, freeing RAM for "
            "active processes. Trading latency (disk) for capacity."
        ),
        "responsibilities": [
            "Store evicted memory pages on disk",
            "Serve page-in requests when swapped pages are accessed",
            "Manage swap priority across multiple swap devices",
            "Track which swap slots are free/used",
        ],
        "kernel_interaction": (
            "kswapd scans for cold pages and writes them to swap via the block layer. "
            "When a process accesses a swapped page, a major page fault triggers "
            "page-in from swap. The kernel uses swap_map[] to track slot usage. "
            "vm.swappiness (0-200) controls how aggressively the kernel swaps."
        ),
        "common_bottlenecks": [
            "Swap thrashing (constant page-in/page-out cycles)",
            "High swap usage indicating memory pressure",
            "Slow swap device (HDD) causing massive latency spikes",
            "Major page fault overhead (blocking the process)",
            "Swap fragmentation reducing I/O efficiency",
        ],
        "related_concepts": [
            "kswapd (kernel swap daemon)",
            "vm.swappiness tunable",
            "zswap/zram (compressed in-memory swap)",
            "Major vs minor page faults",
            "Swap priority and multiple swap areas",
        ],
        "best_practices": [
            "Use SSD or zram for swap (never HDD for production)",
            "Set vm.swappiness=10 for database servers",
            "Monitor with vmstat (si/so columns = swap in/out)",
            "Use zswap for compressed swap caching",
            "Alert if swap usage exceeds 50% of total swap",
        ],
        "documentation": [
            "man 2 swapon — Start/stop swapping to a device",
            "man 8 mkswap — Set up a swap area",
            "Documentation/admin-guide/sysctl/vm.rst",
        ],
    },

    "nic": {
        "title": "Network Interface Controller",
        "purpose": (
            "The physical or virtual hardware that sends and receives network "
            "packets. Modern NICs support hardware offloading, RSS (Receive Side "
            "Scaling), and XDP for high-performance packet processing."
        ),
        "responsibilities": [
            "Transmit and receive Ethernet frames",
            "Perform checksum offloading (TCP/UDP/IP)",
            "Distribute incoming packets across CPU cores (RSS)",
            "Support VLAN tagging and stripping",
            "Handle interrupt coalescing for efficiency",
        ],
        "kernel_interaction": (
            "NIC drivers register with the kernel's net_device subsystem. Incoming "
            "packets trigger interrupts → NAPI polling → sk_buff allocation → protocol "
            "stack. The kernel configures the NIC via ethtool ioctls. XDP hooks allow "
            "processing packets before sk_buff allocation."
        ),
        "common_bottlenecks": [
            "IRQ affinity misconfiguration (one core handling all interrupts)",
            "Ring buffer overflow (packet drops)",
            "TCP segmentation offload (TSO) bugs",
            "Interrupt coalescing too aggressive (latency) or too light (CPU)",
            "PCIe bandwidth saturation on high-throughput NICs",
        ],
        "related_concepts": [
            "NAPI (New API — interrupt mitigation via polling)",
            "RSS (Receive Side Scaling)",
            "XDP (eXpress Data Path)",
            "Ethtool (NIC configuration)",
            "Ring buffers (RX/TX descriptor rings)",
        ],
        "best_practices": [
            "Balance IRQs across cores with irqbalance or manual smp_affinity",
            "Increase ring buffer sizes: ethtool -G eth0 rx 4096",
            "Enable GRO/TSO for throughput workloads",
            "Use XDP for packet filtering at line rate",
            "Monitor drops with ethtool -S eth0 | grep drop",
        ],
        "documentation": [
            "Documentation/networking/scaling.txt in the kernel source",
            "man 8 ethtool — Query or control network driver and hardware",
            "man 7 packet — Packet interface on device level",
        ],
    },

    "ssd": {
        "title": "NVMe / SSD Storage",
        "purpose": (
            "Non-volatile storage using flash memory. NVMe SSDs connect directly "
            "via PCIe for maximum throughput. They have no seek time but have "
            "write amplification and wear leveling concerns."
        ),
        "responsibilities": [
            "Store persistent data (files, databases, swap)",
            "Handle read/write commands from the I/O scheduler",
            "Perform internal garbage collection and wear leveling",
            "Manage the Flash Translation Layer (FTL)",
            "Support TRIM/discard for freed block notification",
        ],
        "kernel_interaction": (
            "NVMe devices use the kernel's nvme driver with multi-queue support "
            "(blk-mq). Commands go through submission/completion queue pairs mapped "
            "directly to CPU cores. The kernel issues TRIM commands via "
            "REQ_OP_DISCARD. SMART data is accessible via nvme-cli."
        ),
        "common_bottlenecks": [
            "Write amplification (internal rewriting of flash pages)",
            "Garbage collection stalls (SSD internal maintenance)",
            "Queue depth saturation (too many concurrent I/Os)",
            "Thermal throttling under sustained write loads",
            "Wear-out (limited P/E cycles per flash cell)",
        ],
        "related_concepts": [
            "NVMe protocol and queues",
            "Flash Translation Layer (FTL)",
            "TRIM / discard operations",
            "Write amplification factor (WAF)",
            "SMART health monitoring",
        ],
        "best_practices": [
            "Enable fstrim.timer for periodic TRIM",
            "Monitor SMART with smartctl or nvme-cli",
            "Use appropriate filesystem (ext4/XFS) with discard mount option",
            "Leave ~10% unpartitioned for over-provisioning",
            "Monitor with iostat -x for await and %util",
        ],
        "documentation": [
            "NVMe specification (nvmexpress.org)",
            "man 1 nvme — NVMe management tool",
            "man 1 iostat — Report I/O statistics",
        ],
    },

    # ══════════════════════════════════════════════════════════════
    # COLUMN 4: EXTERNAL
    # ══════════════════════════════════════════════════════════════

    "dns": {
        "title": "DNS Resolver",
        "purpose": (
            "Translates human-readable domain names (google.com) to IP addresses "
            "(142.250.190.46). DNS resolution is the first step of virtually every "
            "network connection."
        ),
        "responsibilities": [
            "Resolve domain names to IP addresses (A, AAAA records)",
            "Cache DNS responses to avoid repeated lookups",
            "Handle DNS-over-HTTPS (DoH) and DNS-over-TLS (DoT)",
            "Support service discovery (SRV records)",
            "Implement negative caching (NXDOMAIN responses)",
        ],
        "kernel_interaction": (
            "DNS resolution happens in user space (glibc's getaddrinfo → stub resolver "
            "→ /etc/resolv.conf → recursive resolver). The kernel provides the socket "
            "interface for UDP/TCP DNS queries. systemd-resolved or dnsmasq often act "
            "as local caching resolvers."
        ),
        "common_bottlenecks": [
            "DNS latency adding to every new connection",
            "DNS cache misses on first request (cold start)",
            "DNS resolver timeout (5s default in glibc)",
            "NXDOMAIN storms from misconfigured service discovery",
            "DNS-over-HTTPS overhead vs plain UDP DNS",
        ],
        "related_concepts": [
            "DNS record types (A, AAAA, CNAME, MX, SRV, TXT)",
            "TTL (Time To Live) and caching",
            "Recursive vs authoritative resolvers",
            "DNS-over-HTTPS (DoH) and DNS-over-TLS (DoT)",
            "/etc/resolv.conf and nsswitch.conf",
        ],
        "best_practices": [
            "Use a local DNS cache (systemd-resolved, dnsmasq)",
            "Pre-resolve DNS for known services at startup",
            "Monitor DNS latency with dig or drill",
            "Set appropriate TTLs for your DNS records",
            "Use DNS connection pooling in HTTP clients",
        ],
        "documentation": [
            "man 5 resolv.conf — Resolver configuration",
            "man 3 getaddrinfo — Network address and service translation",
            "RFC 1035 — Domain Names: Implementation and Specification",
        ],
    },

    "internet": {
        "title": "Internet / External Network",
        "purpose": (
            "The global interconnected network. Packets leaving your machine "
            "traverse routers, switches, and submarine cables to reach remote "
            "servers. Latency is dominated by physical distance and routing."
        ),
        "responsibilities": [
            "Route packets across autonomous systems (BGP)",
            "Provide last-mile connectivity (ISP)",
            "CDN edge caching for content delivery",
            "TLS termination and certificate validation",
            "Handle packet loss, reordering, and duplication",
        ],
        "kernel_interaction": (
            "The kernel's routing table determines the next hop for outgoing packets. "
            "iptables/nftables apply firewall rules. The kernel handles TCP "
            "retransmissions, congestion control, and connection timeouts. "
            "Traceroute uses ICMP/UDP with increasing TTL to map the path."
        ),
        "common_bottlenecks": [
            "High round-trip time (RTT) to distant servers",
            "Packet loss triggering TCP retransmissions",
            "ISP throttling or traffic shaping",
            "TLS handshake overhead (especially TLS 1.2)",
            "BGP route changes causing temporary unreachability",
        ],
        "related_concepts": [
            "BGP (Border Gateway Protocol)",
            "CDN (Content Delivery Network)",
            "TLS 1.3 (0-RTT, reduced handshake)",
            "TCP congestion control on WAN",
            "Traceroute and MTR for path analysis",
        ],
        "best_practices": [
            "Use CDNs for static content delivery",
            "Enable TLS 1.3 for faster handshakes",
            "Monitor latency with mtr (continuous traceroute)",
            "Use connection pooling / keep-alive",
            "Implement retry with exponential backoff",
        ],
        "documentation": [
            "man 8 traceroute — Print the route packets trace",
            "man 8 mtr — Network diagnostic tool",
            "RFC 793 — TCP specification",
        ],
    },
}


def get_learning_html(node_id: str, accent_color: str, text_color: str, muted_color: str) -> str:
    """Generate rich HTML content for Learning Mode inspector."""
    entry = KNOWLEDGE.get(node_id)
    if not entry:
        return f"<p style='color:{muted_color}'>No learning content available for '{node_id}'.</p>"

    html = f"<h3 style='color:{accent_color}; margin:0 0 8px 0;'>{entry['title']}</h3>"

    # Purpose
    html += f"<p style='color:{text_color}; font-size:12px; line-height:1.5;'>{entry['purpose']}</p>"

    # Responsibilities
    html += f"<h4 style='color:{accent_color}; margin:12px 0 4px 0; font-size:12px;'>📋 RESPONSIBILITIES</h4>"
    html += "<ul style='margin:0; padding-left:16px;'>"
    for r in entry["responsibilities"]:
        html += f"<li style='color:{text_color}; font-size:11px; margin:2px 0;'>{r}</li>"
    html += "</ul>"

    # Kernel interaction
    html += f"<h4 style='color:{accent_color}; margin:12px 0 4px 0; font-size:12px;'>🔧 KERNEL INTERACTION</h4>"
    html += f"<p style='color:{text_color}; font-size:11px; line-height:1.4;'>{entry['kernel_interaction']}</p>"

    # Common bottlenecks
    html += f"<h4 style='color:{accent_color}; margin:12px 0 4px 0; font-size:12px;'>⚠️ COMMON BOTTLENECKS</h4>"
    html += "<ul style='margin:0; padding-left:16px;'>"
    for b in entry["common_bottlenecks"]:
        html += f"<li style='color:#fbbf24; font-size:11px; margin:2px 0;'>{b}</li>"
    html += "</ul>"

    # Related concepts
    html += f"<h4 style='color:{accent_color}; margin:12px 0 4px 0; font-size:12px;'>📚 RELATED CONCEPTS</h4>"
    html += "<ul style='margin:0; padding-left:16px;'>"
    for c in entry["related_concepts"]:
        html += f"<li style='color:{muted_color}; font-size:11px; margin:2px 0;'>{c}</li>"
    html += "</ul>"

    # Best practices
    html += f"<h4 style='color:{accent_color}; margin:12px 0 4px 0; font-size:12px;'>✅ BEST PRACTICES</h4>"
    html += "<ul style='margin:0; padding-left:16px;'>"
    for bp in entry["best_practices"]:
        html += f"<li style='color:#34d399; font-size:11px; margin:2px 0;'>{bp}</li>"
    html += "</ul>"

    # Documentation
    html += f"<h4 style='color:{accent_color}; margin:12px 0 4px 0; font-size:12px;'>📖 DOCUMENTATION</h4>"
    html += "<ul style='margin:0; padding-left:16px;'>"
    for d in entry["documentation"]:
        html += f"<li style='color:{muted_color}; font-size:11px; margin:2px 0;'>{d}</li>"
    html += "</ul>"

    return html
