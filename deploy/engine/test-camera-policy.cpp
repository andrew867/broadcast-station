#include "camera_policy.h"
#include <cassert>
using caspar::ffmpeg::camera_prefix_matches;
int main() {
 assert(camera_prefix_matches("rtsp://source-hub:8554/cam1", "rtsp://source-hub:8554/"));
 assert(camera_prefix_matches("rtsp://upstream:8554/nested/cam", "rtsp://upstream:8554/nested/"));
 assert(camera_prefix_matches("rtmps://upstream/cam", "rtmps://upstream/"));
 assert(!camera_prefix_matches("rtsp://source-hub:8554/cam1", ""));
 assert(!camera_prefix_matches("rtsp://source-hub:85540/cam1", "rtsp://source-hub:8554/"));
 assert(!camera_prefix_matches("rtsp://upstream/other/cam", "rtsp://upstream/nested/"));
 assert(!camera_prefix_matches("rtsp://upstream/", "rtsp://upstream/"));
 assert(!camera_prefix_matches("rtsp:///cam", "rtsp:///"));
 assert(!camera_prefix_matches("music.wav", "music"));
 assert(!camera_prefix_matches("https://example.com/video", "https://example.com/"));
}
