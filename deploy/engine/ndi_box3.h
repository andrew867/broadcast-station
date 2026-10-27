#pragma once
#include <cstdint>
#include <cstddef>

namespace caspar { namespace newtek {
// Exact 3:1 box reduction of packed BGRA. Every source pixel contributes,
// avoiding nearest-neighbour aliasing in the small confidence picture.
// Caller supplies distinct, naturally aligned packed 32-bit image buffers.
inline void ndi_box3(const uint32_t* src, uint32_t* dst, int width, int height)
{
    const int source_width = width * 3;
    for (int y = 0; y < height; ++y) {
        const uint32_t* a = src + size_t(y * 3) * source_width;
        const uint32_t* b = a + source_width;
        const uint32_t* c = b + source_width;
        for (int x = 0; x < width; ++x) {
            const int i = x * 3;
            uint32_t rb = 0, ga = 0;
            for (int k = 0; k < 3; ++k) {
                rb += (a[i+k] & 0x00ff00ff) + (b[i+k] & 0x00ff00ff) + (c[i+k] & 0x00ff00ff);
                ga += ((a[i+k] >> 8) & 0x00ff00ff) + ((b[i+k] >> 8) & 0x00ff00ff) + ((c[i+k] >> 8) & 0x00ff00ff);
            }
            dst[size_t(y) * width + x] = ((rb & 0xffff) + 4) / 9
                | (((ga & 0xffff) + 4) / 9 << 8)
                | (((rb >> 16) + 4) / 9 << 16)
                | (((ga >> 16) + 4) / 9 << 24);
        }
    }
}
}}
