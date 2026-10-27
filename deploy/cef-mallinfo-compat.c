/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Compatibility workaround for CEF's legacy mallinfo telemetry overflow.
 * It changes diagnostic counters only, never allocation or deallocation.
 * glibc's 64-bit mallinfo2 is scaled into coherent nonnegative int counters.
 */
#include <malloc.h>
#include <limits.h>
#include <stdint.h>
static int bounded(size_t n) { return n > INT_MAX ? INT_MAX : (int)n; }
struct mallinfo mallinfo(void) {
    struct mallinfo2 m=mallinfo2();
    struct mallinfo out={0};
    size_t total=m.arena > SIZE_MAX-m.hblkhd ? SIZE_MAX : m.arena+m.hblkhd;
    long double scale=total>INT_MAX?(long double)INT_MAX/total:1.0L;
    out.arena=(int)(m.arena*scale);
    out.hblkhd=(int)(m.hblkhd*scale);
    out.uordblks=(int)(m.uordblks*scale);
    if(out.uordblks>out.arena)out.uordblks=out.arena;
    out.fordblks=out.arena-out.uordblks;
    out.ordblks=bounded(m.ordblks);out.smblks=bounded(m.smblks);out.hblks=bounded(m.hblks);
    out.fsmblks=(int)(m.fsmblks*scale);out.keepcost=(int)(m.keepcost*scale);
    return out;
}
