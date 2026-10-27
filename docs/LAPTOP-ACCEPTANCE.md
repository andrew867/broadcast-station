# Commission an Intel station

Commission the station separately from any existing broadcast. Intel HD30 is the starting profile. The [tested T480s workload](INTEL-STANDBY-20261024.md) does not guarantee equivalent performance on another machine. Output encoding uses the CPU through libx264; the Intel GPU is used for OpenGL and VAAPI camera-health decoding. The Intel profile decodes the complete stream and selects every third picture before downloading and resizing the small health previews on the CPU, because some older Intel/free drivers decode H.264 but reject VAAPI video-processing scaling. This reduces preview work without duplicating stale frames. Very low-rate cameras need the default stride of one instead. QSV output encoding is not qualified.

## Before starting the station

Install Linux x86_64, Docker Engine, Compose and Buildx, Python 3 and FFmpeg. Desktop output also requires a working graphical session, xauth and glxinfo; use a terminal inside that session. A plain SSH session may lack desktop display/audio access. For operation without a desktop, follow [headless setup](HEADLESS.md) and use `stationctl.py check /path/to/station --gpu intel`; the host-readiness report below tests desktop prerequisites.

From the source checkout, collect a read-only report:

```sh
python3 tools/host_readiness.py --gpu intel --output laptop-readiness.json
```

This checks the host without pulling images, launching containers, changing settings or testing network throughput. It does not collect display cookies or credentials. An exit status of 2 means prerequisites are missing. A successful report still does not prove that CasparCG can render through the container or sustain HD30. If OpenGL reports llvmpipe or softpipe, fix the desktop graphics driver before proceeding.

The current Intel profile expects the Intel GPU at `/dev/dri/renderD128`. A different node is reported as a blocker rather than silently selecting another GPU. The readiness report lists the detected nodes and drivers.

## Create a fresh station

```sh
python3 tools/stationctl.py init "$HOME/station-laptop" --gpu intel
```

The Intel initializer selects 1080p30, libx264 and an 8 Mbps starting bitrate. Publishing, HDMI, desktop sound, external providers and playout remain off. Existing station files are never overwritten by `prepare`.

Review `station.json`. For the first engine test, enable only `output.playout`; leave publishing and external providers off. Enable HDMI only when the intended display index and rectangle are known. Add desktop audio separately once the picture works. The graphics canvas is still UHD internally, so the HD output setting does not eliminate all UHD rendering cost.

```sh
python3 tools/stationctl.py check "$HOME/station-laptop" --gpu intel
python3 tools/stationctl.py start "$HOME/station-laptop" --gpu intel
```

The first start builds both images and may take substantial time on this laptop. Previously tested private images can be loaded separately; `resume` starts existing images without building. Keep their exact image IDs with the test record. The readiness check does not download them.

Open `http://127.0.0.1:8765/studio`. Add synthetic cameras first, then one real feed and finally the intended camera count. Use a separate test relay path when enabling publishing. Never use the production program path, production AMCP endpoint or copied paid-provider credentials. Do not copy the production auto-start files onto this laptop.

## Acceptance record

Record these results in order:

1. Host readiness report, Linux version, GPU renderer, image IDs and desktop session type.
2. CasparCG startup OpenGL vendor/version, native channel format and a visible information slide.
3. One synthetic camera, then a quad, then the intended real-camera workload. Keep the conditions with each measurement.
4. A five-minute private recording with continuous 48 kHz audio, followed by `tools/check_program_recording.py`. Inspect transitions and listen to the recording.
5. At least 30 minutes of the intended workload on AC power, with CPU/GPU use, temperature, throttling and memory observations. Note cooling or power-profile changes.
6. Source disconnect/recovery and controller restart. Perform any engine-hang test only on the positively identified laptop station.
7. Manual stop/resume, then reboot recovery after startup services are installed. Desktop mode needs login and display recovery; headless mode must recover without a login. A reconnect over SSH is not proof that programme output recovered.
8. A bounded longer soak once the preceding checks pass.

Keep exact failures and timings. Lowering workload is a valid experimental result; calling HD30 qualified without that workload is not. See [hardware acceptance](HARDWARE-ACCEPTANCE.md) for the detailed recording and recovery procedure.

Stop only this test station with:

```sh
python3 tools/stationctl.py stop "$HOME/station-laptop" --gpu intel
```

Exclude the station data and recording folder from desktop content indexing if it causes background load. Do not disable unrelated desktop services globally. Verify recordings on a different computer where practical; a full decode can compete with the station.
