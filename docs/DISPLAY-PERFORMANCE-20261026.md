# NVIDIA display-mode comparison

## Result

The GeForce RTX 3070 production host rendered the tested UHD60 workload faster in headless EGL mode, but none of the tested modes sustained 60 fps across the camera, quad and aircraft-map scenes. UHD30 remains the commissioned production profile.

| Rendering and display mode | Single camera | Four-camera quad | Aircraft map | Peak sampled GPU memory on quad |
|---|---:|---:|---:|---:|
| Desktop rendering, HDMI preview and desktop audio | 51.96 fps | 47.16 fps | 52.70 fps | 5,931 MiB |
| Desktop rendering, preview disabled, desktop audio retained | 49.93 fps | 48.55 fps | 52.46 fps | 5,195 MiB |
| Headless EGL, desktop manager stopped | 57.74 fps | 54.50 fps | 57.84 fps | 4,106 MiB |

Rates in the table are native programme frame-counter changes divided by elapsed observation time. Sampled instantaneous-rate averages are retained separately. The camera observation without preview included an initial low-rate sample, so differences of a few fps between the desktop cases should not be treated as repeatable rankings.

The inspected desktop quad frames contained four camera pictures. The inspected headless quad frame contained three camera pictures and a fallback slate for the fourth source. Its 54.50 fps result is therefore a measurement of that observed layout, not a matched four-live-input benchmark. All four NTV inputs were decoded and natively ready again after restoration to UHD30. Repeat the quad comparison with recorded source readiness throughout before attributing its entire performance difference to display mode.

Headless used 1,825 MiB less peak sampled GPU memory on the observed quad layout than desktop preview. The source-availability difference prevents treating this entire reduction as desktop overhead. Sampled GPU utilisation during the quad remained approximately 68 to 69 percent in all three modes. These measurements do not identify one exclusive bottleneck. The headless case changes both the rendering backend and the desktop session state, so its improvement cannot be attributed solely to the compositor.

## Method

The tests used the same versioned controller and engine images, UHD60 profile, encoder settings, source catalogue and scene order. Automatic rotation was paused for the comparison. Each mode took the same live camera, four-camera quad and island aircraft map. Each take had 15 seconds of settling time followed by 45 seconds of observations at approximately five-second intervals. All observed programme states were ready and matched the requested scene.

The headless case had an inactive display manager, no graphical login session, no engine display mounts and no display environment variables. Desktop audio was disabled in that mode because it depends on a desktop audio socket. Programme audio remained part of the encoded output.

An independent receiver captured each mode. Packet timing was checked across each complete recording. Three 15-second segments beginning at 20, 80 and 140 seconds were decoded for picture integrity. The initial full-record UHD60 decode exceeded the diagnostic's 180-second single-thread time limit; full-record decoding is therefore not claimed for these performance recordings. Separate HD30 and UHD30 package-acceptance recordings completed their full decode checks.

| Receiver recording | Measured video packet rate | Video intervals above 41.7 ms | Audio gaps above 100 ms |
|---|---:|---:|---:|
| Desktop with preview | 49.10 fps | 160 | 0 |
| Desktop without preview | 47.48 fps | 223 | 0 |
| Headless | 56.60 fps | 14 | 0 |

All three recordings had non-silent 48 kHz audio and clean decoded segments. None met the 60 fps packet-cadence acceptance check. These recording averages include scene changes and settling periods, unlike the scene-specific native counter measurements above.

## Operating recommendation

Use UHD30 for the commissioned production workload. Headless mode provides useful throughput and memory headroom, but this short comparison does not qualify UHD60, overnight headless operation or a physical power-cycle recovery. A configured or advertised 60 fps stream format is not evidence of 60 newly rendered programme frames each second. Individual camera feeds also retain their own capture rates.

The comparison temporarily interrupted output during mode changes. The original UHD30 configuration, desktop HDMI, desktop audio and automatic rundown were restored after the experiment. A final 90-second receiver recording decoded completely at 30.00 fps, with non-silent 48 kHz audio and no large audio or video timestamp gaps. The watchdog and display helper were active; the maintenance marker and temporary restore timer were cleared.

A USB HDMI capture also showed the expected programme picture, graphics and ticker after desktop recovery. Digital audio was present at a low level. The local capture reported buffer drops, so it is evidence of physical output and layout only, not HDMI cadence acceptance. No default output-format change is recommended by this record.

See [package acceptance](PACKAGE-ACCEPTANCE-20261026.md), [headless operation](HEADLESS.md) and the [release checklist](RELEASE-CHECKLIST.md).

## Preview resolution check at UHD30

After the four-hour headless observation, the running UHD30 programme preview was briefly moved from its configured secondary display to a 3840x2160 window on the primary 4K display, then restored. Only the screen consumer was replaced; programme encoding, music and automatic rotation continued. The engine start time and saved station configuration were unchanged.

The screen consumer uses the GPU texture path and OpenGL scaling. This is not a separate CPU video-resize pipeline. The secondary display appeared to Xwayland as a 2784x1566 logical desktop region; the attached HDMI capture receives 1920x1080.

Eight samples per placement showed mean GPU utilisation of 36.5% on the original display, 38.6% on the native 4K display and 37.5% after restoration. Mean GPU memory was approximately 2,481, 2,630 and 2,691 MiB respectively. Engine CPU use was approximately 73%, 86% and 86% of one core. Programme output remained around 30 fps.

These short observations used a changing live rundown, with no fixed-scene or repeated-order control. They do not isolate scaling cost or establish a repeatable performance ranking. They showed no reason to move the preview permanently to the 4K monitor. The original secondary-display placement was restored; the UHD30 baseline remains unchanged.
