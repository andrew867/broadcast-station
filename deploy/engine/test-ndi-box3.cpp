#include "ndi_box3.h"
#include <vector>
#include <cassert>
#include <chrono>
#include <iostream>
extern "C" {
#include <libswscale/swscale.h>
}
int main()
{
    const int w = 1280, h = 720;
    std::vector<uint32_t> src(w*h*9), dst(w*h+2, 0xdeadbeef);
    for (size_t i=0; i<src.size(); ++i) src[i] = uint32_t(i*7919 + i/251);
    caspar::newtek::ndi_box3(src.data(), dst.data()+1, w, h);
    assert(dst.front()==0xdeadbeef && dst.back()==0xdeadbeef);
    for (int y=0; y<h; ++y) for (int x=0; x<w; ++x) {
        uint32_t expected = 0;
        for (int ch=0; ch<4; ++ch) {
            unsigned sum=0;
            for (int dy=0; dy<3; ++dy) for (int dx=0; dx<3; ++dx)
                sum += (src[(y*3+dy)*w*3+x*3+dx] >> (ch*8)) & 255;
            expected |= ((sum+4)/9) << (ch*8);
        }
        assert(dst[1+y*w+x] == expected);
    }
    auto sws = sws_getContext(w*3,h*3,AV_PIX_FMT_BGRA,w,h,AV_PIX_FMT_BGRA,SWS_FAST_BILINEAR,nullptr,nullptr,nullptr);
    assert(sws);
    const uint8_t* in[] = {reinterpret_cast<uint8_t*>(src.data()),nullptr,nullptr,nullptr};
    uint8_t* out[] = {reinterpret_cast<uint8_t*>(dst.data()+1),nullptr,nullptr,nullptr};
    int istride[]={w*12,0,0,0}, ostride[]={w*4,0,0,0};
    for (int mode=0; mode<2; ++mode) {
        auto start=std::chrono::steady_clock::now();
        for(int i=0;i<60;++i) {
            if(mode==0) sws_scale(sws,in,istride,0,h*3,out,ostride);
            else caspar::newtek::ndi_box3(src.data(),dst.data()+1,w,h);
        }
        auto seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::cout << (mode==0 ? "swscale" : "box3") << " milliseconds/frame: " << seconds*1000/60 << std::endl;
    }
    sws_freeContext(sws);
    std::cout << "All 921600 pixels matched independent 9-pixel/channel reference; destination guards intact\n";
}
