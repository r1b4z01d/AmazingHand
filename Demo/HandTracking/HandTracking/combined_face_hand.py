import argparse
import math
import socket
import time

import cv2
import mediapipe as mp
import numpy as np

from eye_renderer import draw_eye
from face_utils import (
    box_top_center,
    pick_face,
    pose_box_from_landmarks,
    schedule_blink,
)
from hand_processing import (
    JOINT_OPEN_OFFSETS,
    format_joint_command,
    generate_joint_offsets,
)
from window_utils import (
    is_global_key_pressed,
    set_windows_window_frame_color,
    supports_global_hotkeys,
)


# ---------- MediaPipe Hands setup ----------
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose


def main():
    parser = argparse.ArgumentParser(description="Eyes + One-hand tracking on one camera")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default 0)")
    parser.add_argument("--width", type=int, default=1280, help="Camera width")
    parser.add_argument("--height", type=int, default=720, help="Camera height")
    parser.add_argument("--show_eyes", action="store_true", help="Show eyes window")
    parser.add_argument("--mirror", action="store_true", help="Mirror hand visuals (selfie style)")
    parser.add_argument("--hand_in_eyes", action="store_true", help="Overlay hand landmarks in a panel below the eyes")
    parser.add_argument("--hand_panel_height", type=int, default=400, help="Height in pixels for the hand panel under the eyes")
    parser.add_argument("--hand_panel_scale", type=float, default=1.0, help="Scale factor for in-eyes hand overlay rendering")
    parser.add_argument("--blink_min", type=float, default=2.5, help="Minimum seconds between blinks")
    parser.add_argument("--blink_max", type=float, default=15.5, help="Maximum seconds between blinks")
    parser.add_argument("--blink_duration", type=float, default=0.18, help="Blink duration in seconds")
    parser.add_argument("--gaze_speed", type=float, default=0.3, help="Smoothing factor (0-1) controlling how fast the eyes chase a tracked target")
    parser.add_argument("--gaze_idle_speed", type=float, default=0.01, help="Smoothing factor (0-1) controlling eye speed during idle wandering")
    parser.add_argument("--relay_hand", action="store_true", help="Stream computed hand joints to the wireless hand over TCP")
    parser.add_argument("--hand_host", type=str, default="192.168.1.194", help="Hand relay TCP host")
    parser.add_argument("--hand_port", type=int, default=8765, help="Hand relay TCP port")
    parser.add_argument("--hand_rate", type=float, default=20.0, help="Maximum hand relay updates per second")
    parser.add_argument("--hand_speed", type=int, default=1000, help="Servo speed value embedded in joint messages")
    parser.add_argument(
        "--save_raw_video",
        type=str,
        nargs="?",
        const="raw_camera.mp4",
        default=None,
        help="Save the raw camera feed to a video file (default raw_camera.mp4 if no path is provided)",
    )
    parser.add_argument(
        "--save_video",
        type=str,
        nargs="?",
        const="combined_output.mp4",
        default=None,
        help="Save the eyes window output to a video file (default combined_output.mp4 if no path is provided)",
    )
    args = parser.parse_args()

    # Single-window design: Eyes window only; hands can render in bottom panel
    show_eyes = True
    hand_stream_enabled = args.relay_hand
    hand_stream_hotkey = "s"
    global_hotkey_supported = supports_global_hotkeys()
    hand_stream_toggle_active = False
    hotkey_prev_state = False
    if hand_stream_enabled:
        if global_hotkey_supported:
            print(
                f"Hand relay armed. Press '{hand_stream_hotkey}' to toggle streaming "
                "(hotkey works even when the window is unfocused)."
            )
        else:
            hand_stream_toggle_active = True
            print(
                "Hand relay armed but global hotkeys are unavailable on this platform; "
                "hand data will stream continuously."
            )
    hand_target_speed = int(min(max(args.hand_speed, 50), 2000))
    hand_socket = None
    last_hand_send = 0.0
    hand_send_interval = 1.0 / max(args.hand_rate, 1e-5)
    hand_idle_timeout = 0.75
    hand_last_detection_time = time.monotonic()
    hand_open_sent = False

    # Camera
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    camera_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or args.width)
    camera_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or args.height)
    capture_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if capture_fps <= 1e-2:
        capture_fps = 30.0

    # Eyes canvas and params
    eye_canvas_width = 1080
    eye_canvas_height = 1900
    window_name = "Robot Disco"
    eye_radius = 90
    eye_white_radius = 220
    eye_top_margin = 80
    eye_side_margin = 80
    eyelid_color = (30, 30, 30)
    draw_eyelashes = True
    eyelash_color = (50, 50, 55)
    eyelash_count = 7
    eyelash_length_top = 55
    eyelash_length_side = 20
    eyelash_thickness = 4

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)
    cv2.resizeWindow(window_name, eye_canvas_width, eye_canvas_height)
    set_windows_window_frame_color(window_name, (0, 0, 0))

    video_fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    raw_video_writer = None
    if args.save_raw_video:
        raw_video_writer = cv2.VideoWriter(
            args.save_raw_video, video_fourcc, capture_fps, (camera_width, camera_height)
        )
        if not raw_video_writer.isOpened():
            print(f"Warning: could not open raw video writer at {args.save_raw_video}")
            raw_video_writer = None

    video_writer = None
    if args.save_video:
        video_writer = cv2.VideoWriter(
            args.save_video, video_fourcc, capture_fps, (eye_canvas_width, eye_canvas_height)
        )
        if not video_writer.isOpened():
            print(f"Warning: could not open video writer at {args.save_video}")
            video_writer = None

    # Face tracking state
    tracked_face = None
    last_seen_time = time.time()
    face_stick_seconds = 1.0
    idle_scan_delay_seconds = 4.0
    idle_scan_period_seconds = 8.0
    idle_scan_horizontal_fraction = 0.25
    idle_scan_vertical_fraction = 0.12
    smoothed_center = None
    def clamp_speed(val):
        return min(max(val, 0.01), 1.0)

    smoothing_factor_active = clamp_speed(args.gaze_speed)
    smoothing_factor_idle = clamp_speed(args.gaze_idle_speed)

    # Blink state
    blink_min_interval_seconds = args.blink_min
    blink_max_interval_seconds = args.blink_max
    blink_duration_seconds = args.blink_duration
    blink_start_time = None
    next_blink_time = schedule_blink(blink_min_interval_seconds, blink_max_interval_seconds)

    # Mediapipe pose + hands (limit to 1 hand)
    with mp_pose.Pose(
        model_complexity=0,
        enable_segmentation=False,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose_detector, mp_hands.Hands(
        max_num_hands=1,
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as hands:

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            if raw_video_writer is not None:
                raw_video_writer.write(frame)

            # ---- Person detection for eyes ----
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame.flags.writeable = False
            pose_results = pose_detector.process(rgb_frame)
            rgb_frame.flags.writeable = True
            faces = []
            if pose_results and pose_results.pose_landmarks:
                pose_box = pose_box_from_landmarks(
                    pose_results.pose_landmarks, camera_width, camera_height
                )
                if pose_box is not None:
                    faces.append(pose_box)

            current_time = time.time()
            current_mono = time.monotonic()
            selected_face = pick_face(faces, tracked_face)
            if selected_face is not None:
                tracked_face = selected_face
                last_seen_time = current_time
            elif current_time - last_seen_time > face_stick_seconds:
                tracked_face = None

            time_since_face = current_time - last_seen_time
            if tracked_face is not None:
                center = box_top_center(tracked_face)
            elif time_since_face > idle_scan_delay_seconds:
                scan_elapsed = time_since_face - idle_scan_delay_seconds
                sweep_angle = (2 * math.pi / idle_scan_period_seconds) * scan_elapsed
                center = (
                    camera_width / 2.0 + math.sin(sweep_angle) * camera_width * idle_scan_horizontal_fraction,
                    camera_height / 2.0 + math.cos(sweep_angle * 0.7) * camera_height * idle_scan_vertical_fraction,
                )
            else:
                center = (camera_width / 2.0, camera_height / 2.0)

            if smoothed_center is None:
                smoothed_center = center
            else:
                current_smoothing = (
                    smoothing_factor_active if tracked_face is not None else smoothing_factor_idle
                )
                smoothed_center = (
                    smoothed_center[0] + (center[0] - smoothed_center[0]) * current_smoothing,
                    smoothed_center[1] + (center[1] - smoothed_center[1]) * current_smoothing,
                )

            if blink_start_time is None and current_mono >= next_blink_time:
                blink_start_time = current_mono

            if blink_start_time is not None:
                elapsed = current_mono - blink_start_time
                half = blink_duration_seconds / 2.0
                if elapsed >= blink_duration_seconds:
                    blink_start_time = None
                    next_blink_time = schedule_blink(
                        blink_min_interval_seconds, blink_max_interval_seconds
                    )
                    blink_amount = 0.0
                else:
                    if elapsed <= half:
                        blink_amount = min(1.0, elapsed / half)
                    else:
                        blink_amount = max(0.0, 1.0 - ((elapsed - half) / half))
            else:
                blink_amount = 0.0

            # Gaze mapping normalized by camera dims
            norm_x = (smoothed_center[0] - camera_width / 2.0) / (camera_width / 2.0)
            norm_y = (smoothed_center[1] - camera_height / 2.0) / (camera_height / 2.0)
            norm_x = max(min(norm_x, 1.0), -1.0)
            norm_y = max(min(norm_y, 1.0), -1.0)

            # Scale by usable pupil travel within the sclera
            max_travel = max(eye_white_radius - eye_radius, 0)
            gaze_gain_x = 0.7
            gaze_gain_y = 0.6
            offsetX = norm_x * max_travel * gaze_gain_x
            offsetY = norm_y * max_travel * gaze_gain_y
            offsetX *= -1.0  # Mirror horizontally so eyes track in the camera reference frame

            # Determine if we need hands processing (for in-eyes overlay or hotkey-triggered streaming)
            if hand_stream_enabled and global_hotkey_supported:
                hotkey_pressed = is_global_key_pressed(hand_stream_hotkey)
                if hotkey_pressed and not hotkey_prev_state:
                    hand_stream_toggle_active = not hand_stream_toggle_active
                    state_str = "enabled" if hand_stream_toggle_active else "paused"
                    print(f"Hand relay {state_str} via '{hand_stream_hotkey}' toggle.")
                hotkey_prev_state = hotkey_pressed
            elif hand_stream_enabled and not global_hotkey_supported:
                hand_stream_toggle_active = True

            hand_stream_active = hand_stream_enabled and hand_stream_toggle_active
            need_hands = (show_eyes and args.hand_in_eyes) or hand_stream_active
            results = None
            if need_hands:
                rgb_frame.flags.writeable = False
                results = hands.process(rgb_frame)
                rgb_frame.flags.writeable = True

            if hand_stream_active:
                hand_payload = None
                if results and results.multi_hand_landmarks:
                    joint_offsets = generate_joint_offsets(results.multi_hand_landmarks[0])
                    hand_payload = format_joint_command(joint_offsets, hand_target_speed)
                    hand_last_detection_time = current_mono
                    hand_open_sent = False
                elif (current_mono - hand_last_detection_time) > hand_idle_timeout and not hand_open_sent:
                    hand_payload = format_joint_command(JOINT_OPEN_OFFSETS, hand_target_speed)
                    hand_open_sent = True

                if (
                    hand_payload is not None
                    and (current_mono - last_hand_send) >= hand_send_interval
                ):
                    if hand_socket is None:
                        try:
                            hand_socket = socket.create_connection(
                                (args.hand_host, args.hand_port), timeout=0.5
                            )
                            hand_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        except OSError:
                            hand_socket = None
                    if hand_socket is not None:
                        try:
                            hand_socket.sendall(hand_payload.encode("ascii"))
                            last_hand_send = current_mono
                        except OSError:
                            hand_socket.close()
                            hand_socket = None

            # Prepare eyes canvas
            if show_eyes:
                eye_canvas = np.zeros((eye_canvas_height, eye_canvas_width, 3), dtype=np.uint8)
                eye_vertical_center = eye_top_margin + eye_white_radius
                left_eye_center = (
                    eye_side_margin + eye_white_radius,
                    eye_vertical_center,
                )
                right_eye_center = (
                    eye_canvas_width - eye_side_margin - eye_white_radius,
                    eye_vertical_center,
                )
                right_center_with_offset = (
                    int(right_eye_center[0] + offsetX),
                    int(right_eye_center[1] + offsetY),
                )
                left_center_with_offset = (
                    int(left_eye_center[0] + offsetX),
                    int(left_eye_center[1] + offsetY),
                )
                draw_eye(
                    eye_canvas,
                    right_eye_center,
                    eye_white_radius,
                    eye_radius,
                    (
                        right_center_with_offset[0] - right_eye_center[0],
                        right_center_with_offset[1] - right_eye_center[1],
                    ),
                    blink_amount,
                    eyelid_color,
                    draw_eyelashes,
                    eyelash_color,
                    eyelash_count,
                    eyelash_length_top,
                    eyelash_length_side,
                    eyelash_thickness,
                )
                draw_eye(
                    eye_canvas,
                    left_eye_center,
                    eye_white_radius,
                    eye_radius,
                    (
                        left_center_with_offset[0] - left_eye_center[0],
                        left_center_with_offset[1] - left_eye_center[1],
                    ),
                    blink_amount,
                    eyelid_color,
                    draw_eyelashes,
                    eyelash_color,
                    eyelash_count,
                    eyelash_length_top,
                    eyelash_length_side,
                    eyelash_thickness,
                )
                # If requested, draw hand landmarks inside the eyes canvas in a bottom panel
                if args.hand_in_eyes and results is not None and results.multi_hand_landmarks:
                    panel_h = max(600, min(args.hand_panel_height, eye_canvas_height))
                    y0 = eye_canvas_height - panel_h
                    x0 = 0
                    hand_panel = eye_canvas[y0:eye_canvas_height, x0:eye_canvas_width]
                    # draw on a temp panel then mirror if requested
                    panel_img = np.zeros_like(hand_panel)
                    mp_drawing.draw_landmarks(
                        panel_img,
                        results.multi_hand_landmarks[0],
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )
                    if args.mirror:
                        panel_img = cv2.flip(panel_img, 1)
                    panel_scale = max(args.hand_panel_scale, 1.0)
                    if panel_scale != 1.0:
                        scaled_img = cv2.resize(
                            panel_img,
                            None,
                            fx=panel_scale,
                            fy=panel_scale,
                            interpolation=cv2.INTER_LINEAR,
                        )
                        target_h, target_w = hand_panel.shape[:2]
                        if scaled_img.shape[0] >= target_h and scaled_img.shape[1] >= target_w:
                            start_y = (scaled_img.shape[0] - target_h) // 2
                            start_x = (scaled_img.shape[1] - target_w) // 2
                            panel_img = scaled_img[start_y : start_y + target_h, start_x : start_x + target_w]
                        else:
                            panel_img = cv2.resize(
                                scaled_img, (target_w, target_h), interpolation=cv2.INTER_LINEAR
                            )
                    hand_panel[:] = panel_img
                if video_writer is not None:
                    video_writer.write(eye_canvas)
                cv2.imshow(window_name, eye_canvas)

            key_code = cv2.waitKey(1) & 0xFF
            if key_code == ord("q"):
                break

    if hand_socket is not None:
        hand_socket.close()
    if raw_video_writer is not None:
        raw_video_writer.release()
    if video_writer is not None:
        video_writer.release()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
