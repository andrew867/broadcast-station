#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#include <libavutil/pixfmt.h>
typedef void (*copy_fn)(uint8_t *const[4], const int[4], const uint8_t *const[4], const int[4], enum AVPixelFormat, int, int);
int main(void) {
    assert(dlopen("libavutil.so.58", RTLD_NOW | RTLD_GLOBAL));
    copy_fn copy = (copy_fn)dlsym(RTLD_DEFAULT, "av_image_copy");
    assert(copy);
    size_t size = 15552 * 2160 + 128;
    uint8_t *src = aligned_alloc(64, size), *dst = aligned_alloc(64, size);
    assert(src && dst);
    for (size_t i = 0; i < size; ++i) src[i] = (uint8_t)(i*17+i/251);
    int checks = 0;
    for (int offset = 0; offset < 2; ++offset) for (int pad = 0; pad < 2; ++pad) {
        int stride = 15360 + pad*64;
        uint8_t *dd[4] = {dst+offset}; const uint8_t *ss[4] = {src+offset};
        int dl[4] = {stride}, sl[4] = {stride};
        memset(dst, 0xad, size);
        copy(dd, dl, ss, sl, AV_PIX_FMT_BGRA, 3840, 2160);
        for(int y=0;y<2160;++y) {
            assert(!memcmp(dst+offset+y*stride, src+offset+y*stride, 15360));
            for (int j=15360;j<stride;++j) assert(dst[offset+y*stride+j]==0xad);
        }
        if(offset) assert(dst[0]==0xad);
        assert(dst[offset+2160*stride]==0xad);
        ++checks;
    }
    free(src); free(dst); printf("%d full-UHD pixel and padding checks passed\n", checks);
}
