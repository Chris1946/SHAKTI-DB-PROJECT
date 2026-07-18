#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <bcc/proto.h>

// Hash map to store the start time of a connection attempt, keyed by process ID
BPF_HASH(start, u32, u64);

// Histogram to track connection latency in microseconds
BPF_HISTOGRAM(tcp_latency_us);

// Called when tcp_v4_connect is entered (process initiates an outbound connection)
int trace_connect_entry(struct pt_regs *ctx, struct sock *sk)
{
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 ts = bpf_ktime_get_ns();
    start.update(&pid, &ts);
    return 0;
}

// Called when tcp_v4_connect returns (connection established or failed)
int trace_connect_return(struct pt_regs *ctx)
{
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 *tsp = start.lookup(&pid);
    
    if (tsp == 0) {
        return 0; // Missed the start event
    }
    
    // Calculate delta and store in histogram
    u64 delta = bpf_ktime_get_ns() - *tsp;
    u64 latency_us = delta / 1000;
    
    tcp_latency_us.increment(bpf_log2l(latency_us));
    
    // Clean up map
    start.delete(&pid);
    
    return 0;
}
