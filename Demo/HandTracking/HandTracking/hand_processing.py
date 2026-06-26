"""Helpers for translating MediaPipe hand landmarks into servo offsets."""

from __future__ import annotations

import math

import numpy as np


JOINT_OPEN_OFFSETS = np.array(
    [-35.0, 35.0, -35.0, 35.0, -35.0, 35.0, -35.0, 35.0], dtype=np.float32
)
JOINT_CLOSE_OFFSETS = np.array(
    [90.0, -90.0, 90.0, -90.0, 90.0, -90.0, 70.0, -70.0], dtype=np.float32
)
FINGER_TO_SERVO = {
    "index": (0, 1),
    "middle": (2, 3),
    "ring": (4, 5),
    "thumb": (6, 7),
}
FINGER_LANDMARK_INDICES = {
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
    "thumb": (1, 2, 3, 4),
}
CURL_MIN_ANGLE = math.radians(60.0)


def _finger_curl(lm_array, idxs):
    mcp = lm_array[idxs[0]]
    pip = lm_array[idxs[1]]
    dip = lm_array[idxs[2]]
    v1 = mcp - pip
    v2 = dip - pip
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 < 1e-5 or norm2 < 1e-5:
        return 0.0
    cos_angle = np.clip(np.dot(v1, v2) / (norm1 * norm2), -1.0, 1.0)
    angle = math.acos(cos_angle)
    curl = (math.pi - angle) / (math.pi - CURL_MIN_ANGLE)
    return float(max(0.0, min(curl, 1.0)))


def _thumb_curl(lm_array):
    angle_component = _finger_curl(lm_array, FINGER_LANDMARK_INDICES["thumb"])
    index_mcp = lm_array[5]
    thumb_tip = lm_array[4]
    wrist = lm_array[0]
    ref_dist = np.linalg.norm(index_mcp - wrist)
    if ref_dist < 1e-5:
        ref_dist = np.linalg.norm(lm_array[9] - wrist)
    if ref_dist < 1e-5:
        dist_component = 0.0
    else:
        dist = np.linalg.norm(thumb_tip - index_mcp)
        dist_component = 1.0 - np.clip(dist / ref_dist, 0.0, 1.0)
    blend = 0.4 * angle_component + 0.6 * dist_component
    return float(max(0.0, min(blend, 1.0)))


def generate_joint_offsets(hand_landmarks):
    lm_array = np.array(
        [[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark], dtype=np.float32
    )
    curls = {}
    for finger, idxs in FINGER_LANDMARK_INDICES.items():
        if finger == "thumb":
            curls[finger] = _thumb_curl(lm_array)
        else:
            curls[finger] = _finger_curl(lm_array, idxs)
    if "pinky" in curls:
        curls["ring"] = curls["pinky"]
    joint_offsets = np.array(JOINT_OPEN_OFFSETS, copy=True)
    for finger, servo_indices in FINGER_TO_SERVO.items():
        curl = curls.get(finger, 0.0)
        for idx in servo_indices:
            open_val = JOINT_OPEN_OFFSETS[idx]
            close_val = JOINT_CLOSE_OFFSETS[idx]
            joint_offsets[idx] = open_val + (close_val - open_val) * curl
    return joint_offsets


def format_joint_command(values, speed):
    arr = np.asarray(values, dtype=np.float32).tolist()
    payload = ",".join(f"{val:.2f}" for val in arr)
    return f"J:{payload},{int(speed)}\n"


__all__ = [
    "JOINT_OPEN_OFFSETS",
    "generate_joint_offsets",
    "format_joint_command",
]
