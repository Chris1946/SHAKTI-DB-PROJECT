#include <uapi/linux/ptrace.h>
#include <linux/blkdev.h>
#include <linux/blk-mq.h>

BPF_HISTOGRAM(dist);

// Hook for blk_account_io_done (called when block I/O completes)
int trace_req_done(struct pt_regs *ctx, struct request *req)
{
    // Check if the request actually has a start time
    u64 start_time = req->start_time_ns;
    if (start_time == 0) {
        return 0; // Not a valid timing trace
    }

    // Calculate latency
    u64 delta = bpf_ktime_get_ns() - start_time;
    
    // Store latency in microsecond buckets in the histogram
    u64 latency_us = delta / 1000;
    dist.increment(bpf_log2l(latency_us));

    return 0;
}
