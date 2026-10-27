/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Use FFmpeg's own GPU-mapped-memory copier for aligned UHD BGRA frames.
 * All other formats and alignments retain the original implementation.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stddef.h>
#include <stdatomic.h>
#include <unistd.h>
#include <stdlib.h>
#include <libavutil/pixfmt.h>

typedef void (*copy_fn)(uint8_t *const[4], const int[4], const uint8_t *const[4], const int[4], enum AVPixelFormat, int, int);
typedef void (*uc_fn)(uint8_t *const[4], const ptrdiff_t[4], const uint8_t *const[4], const ptrdiff_t[4], enum AVPixelFormat, int, int);
static atomic_int announced;

void av_image_copy(uint8_t *const dst[4], const int dl[4], const uint8_t *const src[4], const int sl[4], enum AVPixelFormat format, int width, int height) {
    copy_fn original = (copy_fn)dlsym(RTLD_NEXT, "av_image_copy");
    uc_fn optimized = (uc_fn)dlsym(RTLD_NEXT, "av_image_copy_uc_from");
    if (optimized && format == AV_PIX_FMT_BGRA && width == 3840 && height == 2160 &&
        dl[0] >= width * 4 && sl[0] >= width * 4 &&
        !((uintptr_t)dst[0] % 64) && !((uintptr_t)src[0] % 64) && !(dl[0] % 64) && !(sl[0] % 64)) {
        ptrdiff_t ds[4] = {dl[0], dl[1], dl[2], dl[3]};
        ptrdiff_t ss[4] = {sl[0], sl[1], sl[2], sl[3]};
        optimized(dst, ds, src, ss, format, width, height);
        if (!atomic_exchange(&announced, 1)) {
            const char msg[] = "SkyCam: FFmpeg GPU-memory image copy active\n";
            ssize_t written = write(2, msg, sizeof(msg)-1);
            (void)written;
        }
        return;
    }
    if (!original) abort();
    original(dst, dl, src, sl, format, width, height);
}
