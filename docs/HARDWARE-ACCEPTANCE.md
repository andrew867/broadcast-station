# Hardware acceptance before migration

Keep the existing station running until this checklist has recorded results. A successful build or a responsive web page does not establish working video output.

## Separate the test station

Use a new station directory, Compose project and host ports. Use synthetic cameras and a private relay destination. Disable external data providers and leave production credentials out of the test directory. Do not publish to an existing on-air path or share an AMCP endpoint with another controller.

Limit the candidate's CPU and memory while it shares a production host. Check both system and GPU headroom before starting it. Stop the candidate if it affects the live station. Use the same image IDs throughout a test and retain those IDs with the results.

## Picture and sound

1. Retain the native startup log's `Initialized OpenGL` version/vendor line and a successful `GL INFO` response. The latter reports OpenGL resource pools, not the vendor. A software renderer is useful for CI but does not qualify the GPU.
2. Record the private encoded output. Check its dimensions, actual cadence, 48 kHz audio and decode integrity. Review pictures from single-camera and quad scenes, including transition frames.
3. Use two distinct test pictures and a known audio signal. This makes incorrect scene routing and missing sound observable without licensed media or live feeds.
4. Check local sound separately. An isolated PipeWire/PulseAudio sink can prove that the candidate delivers sound to the desktop audio server without changing the operator's listening sink. This does not establish HDMI sound or speaker quality.
5. Test the actual display and listening sink during the migration window. Record the selected display, output mode and audio route. Do not substitute a streamed recording for this check.

For a local recording:

```sh
python3 tools/check_program_recording.py acceptance.mkv --fps 30 --report acceptance.json
```

The tool checks packet cadence, backward or duplicate timestamps, large gaps, the requested video rate within two percent, 48 kHz audio, stream-start/end coverage and complete FFmpeg decoding. It permits a video join within one two-second GOP, but rejects audio joining over one second after video or streams ending over one second apart. This is a continuity check, not a lip-sync measurement. Its report is not a visual review or a listening test. Keep the recording so those can be performed separately.

## Recovery

Run one watchdog for the test station. A second instance must refuse to start rather than use a separate restart budget.

- Disconnect one synthetic camera. Confirm that decoded-frame health changes, program output continues and the complete scene remains available. Restore it and confirm fresh decoded pictures return.
- Stop the private relay briefly. Restore it and confirm the publisher reconnects. Retain recordings before and after, and state the outage duration. This does not establish behavior for an indefinitely unavailable destination.
- Hang the candidate engine process while leaving its container running. Confirm that the watchdog restores it and that picture and sound return. Never inject faults into an unidentified container.
- Hang the controller. Confirm recovery without restarting an otherwise healthy engine.
- Enable maintenance and verify the watchdog's suppression status. Deliberately stop the candidate and verify it stays stopped. Resume it explicitly.
- Refresh the display credentials and recreate the candidate engine. Check picture and sound again. An actual logout/login and reboot still need separate evidence.

Use the guard's real startup grace and recovery cooldown for integration checks. Accelerated unit-test clocks are useful for logic coverage, but do not establish recovery times on the machine.

## Before the production switch

Refresh the settings snapshot, preserve the established images and configuration, and test rollback without overwriting newer operator edits. Qualify HDMI and the actual listening route, then perform the reboot/login drill and a full candidate soak. The existing station's uptime does not count as a candidate soak.

The tested T480s supports the limited HD30 workload recorded in [Intel standby acceptance](INTEL-STANDBY-20261024.md). A different machine, driver or workload requires its own acceptance. For headless installations, replace desktop credential and HDMI checks with the service and receiver checks in [headless operation](HEADLESS.md); cold boot without login remains a separate test.
