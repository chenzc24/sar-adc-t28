# VNC recovery after host restart

Goal: diagnose the user's login errors and restore their stopped desktop.
Owner: current support chat; separate from ongoing SAR8 circuit work.
Local owned: this plan and a concise appended plan/log.md entry.
Existing unrelated Obsidian, management and SAR8 changes remain untouched.
Remote OA: none. Circuit netlists, PDK, models and shared shell scripts read-only.

Remote owned runtime: chenzc_intern25 on thu-jin, display24, existing VNC
configuration read-only; ~/.vnc/thu-jin:24.log and automatic runtime PID/locks.
Preserve prior log as thu-jin:24.log.pre-20261027-recovery without overwriting
an existing backup. No other displays/processes or host services may be stopped.
No password/configuration change, system service restart or compute submission.

Evidence: direct SSH to thu-jin and ProxyJump through it to thu-wei succeed.
Both list no VNC sessions. thu-jin port5924 and X24 locks absent. Shared home
accessible. thu-wei user-596.slice active with48GiB limit at observation.
Both hosts show uptime about9.5h; prior desktop was thu-jin:24, not thu-wei.

Steps: preserve/read back old log; start existing user VNC display24 once with
the user's existing depth24 convention; inspect process, listener and new log.
If unsuccessful, preserve output and diagnose the exact error before retrying.
Validation: vncserver list, owned Xvnc process, port5924 listener, running desktop
session and no immediate session-exit error. Viewer connection remains a user
confirmation, not implied by a successful listening socket.
Commit policy: no commit or push. Record actual result and residual login issue.

## Observed result

Prior display24 log preserved with matching SHA256
caad557e4d705310f3438c0b2ea32a6bf83f64829291130fa5908c9b9ff2d5ff.
One display24 start attempt was refused by the administrator's existing
single-session wrapper. No bypass or repeated start. Fresh inspection found
display3 already running, PID23203, started2026-10-27 08:16:37 Asia/Shanghai,
GNOME session/shell processes present,1920x1080 depth24, TCP5903 listening.
This session is not attributed to our refused display24 attempt. Existing
session preserved; no process killed, configuration edited or lock deleted.
Viewer endpoint is thu-jin:3; suggested tunnel15903->127.0.0.1:5903 on thu-jin.
Desktop pixels/viewer authentication have not been verified by this chat.

Residual LD_LIBRARY_PATH warning reproduces on thu-jin login; user .cshrc
sources /home/dmanager/shared_lib/common/cshrc_main. That shared script has
LD_LIBRARY_PATH expansions at lines118/169; exact failing line is not proven.
No shared or personal startup script changed. Prior PAM user-slice failure
requires administrator review if it recurs; current thu-wei unit is active.
