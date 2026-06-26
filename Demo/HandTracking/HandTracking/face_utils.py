"""Utility helpers for translating pose detections into eye targets."""

from __future__ import annotations

import random
import time
from typing import Sequence, Tuple

import numpy as np


def face_center(face: Sequence[float]) -> Tuple[float, float]:
    x, y, w, h = face
    return (x + w / 2.0, y + h / 2.0)


def box_top_center(box: Sequence[float]) -> Tuple[float, float]:
    x, y, w, h = box
    return (x + w / 2.0, y)


def pick_face(faces, tracked_face):
    if isinstance(faces, np.ndarray):
        faces = faces.tolist()
    if not faces:
        return None
    largest_face = max(faces, key=lambda f: f[2] * f[3])
    if tracked_face is None:
        return largest_face

    tracked_center = face_center(tracked_face)

    def distance(candidate):
        cx, cy = face_center(candidate)
        dx = cx - tracked_center[0]
        dy = cy - tracked_center[1]
        return (dx * dx + dy * dy) ** 0.5

    closest_face = min(faces, key=distance)
    dist = distance(closest_face)
    follow_threshold = max(tracked_face[2], tracked_face[3]) * 0.8 + 40
    return closest_face if dist < follow_threshold else largest_face


def schedule_blink(min_interval, max_interval):
    # Use monotonic clock for robust timing independent of system time changes
    return time.monotonic() + random.uniform(min_interval, max_interval)


POSE_VISIBILITY_THRESHOLD = 0.4


def pose_box_from_landmarks(pose_landmarks, image_width, image_height):
    xs = []
    ys = []
    for lm in pose_landmarks.landmark:
        if lm.visibility < POSE_VISIBILITY_THRESHOLD:
            continue
        xs.append(lm.x)
        ys.append(lm.y)
    if not xs or not ys:
        return None
    x_min = np.clip(min(xs), 0.0, 1.0)
    y_min = np.clip(min(ys), 0.0, 1.0)
    x_max = np.clip(max(xs), 0.0, 1.0)
    y_max = np.clip(max(ys), 0.0, 1.0)
    w = int(round((x_max - x_min) * image_width))
    h = int(round((y_max - y_min) * image_height))
    if w <= 0 or h <= 0:
        return None
    x_px = int(round(x_min * image_width))
    y_px = int(round(y_min * image_height))
    return (x_px, y_px, w, h)


__all__ = [
    "face_center",
    "box_top_center",
    "pick_face",
    "schedule_blink",
    "POSE_VISIBILITY_THRESHOLD",
    "pose_box_from_landmarks",
]
