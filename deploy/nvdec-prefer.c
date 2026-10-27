/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Route H.264 decoding to the available NVIDIA CUVID decoder in this installation.
 * No packet, frame, pixel, timing or allocation APIs are changed.
 * NVIDIA profile only. Intel/software profiles omit this decoder override.
 * Falls back to the installed software decoder when CUVID is not compiled in.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <libavcodec/codec_id.h>
struct AVCodec;
typedef const struct AVCodec *(*find_id)(enum AVCodecID);
typedef const struct AVCodec *(*find_name)(const char *);
const struct AVCodec *avcodec_find_decoder(enum AVCodecID id) {
    find_id original=(find_id)dlsym(RTLD_NEXT,"avcodec_find_decoder");
    find_name named=(find_name)dlsym(RTLD_NEXT,"avcodec_find_decoder_by_name");
    if(id==AV_CODEC_ID_H264 && named){
        const struct AVCodec *gpu=named("h264_cuvid");
        if(gpu)return gpu;
    }
    return original?original(id):0;
}

