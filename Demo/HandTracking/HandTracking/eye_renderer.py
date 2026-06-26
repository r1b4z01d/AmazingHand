"""Rendering helpers for the animated eye canvas."""

from __future__ import annotations

import math

import cv2
import numpy as np


def draw_eye(
    canvas,
    center,
    sclera_radius,
    pupil_radius,
    pupil_offset,
    blink_amount,
    eyelid_color,
    draw_eyelashes,
    eyelash_color,
    eyelash_count,
    eyelash_length_top,
    eyelash_length_side,
    eyelash_thickness,
):
    cx, cy = center
    # Clamp pupil offset so the pupil stays inside the sclera
    dx = float(pupil_offset[0])
    dy = float(pupil_offset[1])
    max_dist = max(sclera_radius - pupil_radius, 0)
    dist = math.hypot(dx, dy)
    if dist > max_dist and dist != 0:
        s = max_dist / dist
        dx *= s
        dy *= s
    pupil_center = (int(cx + dx), int(cy + dy))
    cv2.circle(canvas, (int(cx), int(cy)), sclera_radius, (255, 255, 255), -1)
    cv2.circle(canvas, pupil_center, pupil_radius, (0, 0, 0), -1)

    # Shared blink geometry so lashes can follow the lid even when fully open
    coverage = max(0.0, min(1.0, blink_amount))
    lid_radius = sclera_radius + 8
    top_offset = lid_radius * (1.0 - coverage)
    bottom_offset = lid_radius * (1.0 - coverage)
    top_lid_center = (cx, cy - top_offset)

    if blink_amount > 0.0:
        # Half-circle eyelids that slide toward the eye center as the blink closes
        top_offset_i = int(top_offset)
        bottom_offset_i = int(bottom_offset)
        cv2.ellipse(
            canvas,
            (int(cx), int(cy) - top_offset_i),
            (lid_radius, lid_radius),
            0,
            180,
            360,
            eyelid_color,
            -1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            canvas,
            (int(cx), int(cy) + bottom_offset_i),
            (lid_radius, lid_radius),
            0,
            0,
            180,
            eyelid_color,
            -1,
            lineType=cv2.LINE_AA,
        )

    if draw_eyelashes and eyelash_count > 0:
        lash_positions = np.linspace(-1.0, 1.0, eyelash_count)
        angles = np.linspace(math.pi + 0.35, 2 * math.pi - 0.35, eyelash_count)
        for angle, pos in zip(angles, lash_positions):
            blend = abs(pos)
            length = int(
                round(
                    eyelash_length_top
                    - (eyelash_length_top - eyelash_length_side) * min(blend, 1.0)
                )
            )
            eye_anchor_x = cx + sclera_radius * math.cos(angle)
            eye_anchor_y = cy + sclera_radius * math.sin(angle)
            lid_anchor_x = top_lid_center[0] + lid_radius * math.cos(angle)
            lid_anchor_y = top_lid_center[1] + lid_radius * math.sin(angle)
            follow = coverage
            start_x = int(round((1.0 - follow) * eye_anchor_x + follow * lid_anchor_x))
            start_y = int(round((1.0 - follow) * eye_anchor_y + follow * lid_anchor_y))
            normal_x = math.cos(angle)
            normal_y = math.sin(angle)
            end_x = int(start_x + normal_x * length)
            end_y = int(start_y + normal_y * length)
            cv2.line(
                canvas,
                (start_x, start_y),
                (end_x, end_y),
                eyelash_color,
                eyelash_thickness,
                lineType=cv2.LINE_AA,
            )


__all__ = ["draw_eye"]
