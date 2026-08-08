"""
Frame Validator
===============
Runs BEFORE inference to reject frames that would produce meaningless predictions.

Checks (in order):
  1. Frame decode  — is the base64 image valid?
  2. Frame quality — not too dark, not blank
  3. Hand presence — MediaPipe detects at least one hand with 21 landmarks
  4. Landmark completeness — all 21 landmarks are within the frame bounds

Returns a ValidationResult so the caller can return a meaningful message
to the learner instead of a silent wrong prediction.
"""

import cv2
import base64
import logging
import numpy as np
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_valid:       bool
    hand_detected:  bool
    frame_valid:    bool
    landmarks:      Optional[list]   # raw MediaPipe landmark list if detected
    message:        str              # shown to learner on failure
    error_code:     str              # INVALID_FRAME | NO_HAND | LOW_QUALITY | OK


class FrameValidator:
    """
    Stateless validator — safe to share as a singleton.
    Loads MediaPipe once on init.
    """

    BRIGHTNESS_MIN  = 30    # avg pixel value — reject if too dark
    BRIGHTNESS_MAX  = 240   # reject if completely washed out
    MIN_HAND_CONF   = 0.5

    def __init__(self, mediapipe_task_path: str):
        self._landmarker = None
        self._mp         = None
        self._task_path  = mediapipe_task_path
        self._load_mediapipe()

    def _load_mediapipe(self):
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python.vision import (
                HandLandmarker, HandLandmarkerOptions, RunningMode
            )

            options = HandLandmarkerOptions(
                base_options=python.BaseOptions(
                    model_asset_path=self._task_path
                ),
                num_hands=1,
                min_hand_detection_confidence=self.MIN_HAND_CONF,
                min_hand_presence_confidence=self.MIN_HAND_CONF,
                min_tracking_confidence=self.MIN_HAND_CONF,
                running_mode=RunningMode.IMAGE
            )
            self._landmarker = HandLandmarker.create_from_options(options)
            self._mp         = mp
            logger.info("FrameValidator: MediaPipe loaded.")
        except Exception as e:
            logger.error(f"FrameValidator: failed to load MediaPipe — {e}")
            raise

    # ── Public API ────────────────────────────────────────────────────────────

    def validate(self, frame_base64: str) -> ValidationResult:
        """
        Full validation pipeline.
        Input : base64-encoded JPEG/PNG string from webcam
        Output: ValidationResult
        """
        # ── Step 1: Decode frame ──────────────────────────────────────────
        frame = self._decode_frame(frame_base64)
        if frame is None:
            return ValidationResult(
                is_valid      = False,
                hand_detected = False,
                frame_valid   = False,
                landmarks     = None,
                message       = "Could not decode the image. Please try again.",
                error_code    = "INVALID_FRAME"
            )

        # ── Step 2: Frame quality ─────────────────────────────────────────
        quality_ok, quality_msg = self._check_quality(frame)
        if not quality_ok:
            return ValidationResult(
                is_valid      = False,
                hand_detected = False,
                frame_valid   = False,
                landmarks     = None,
                message       = quality_msg,
                error_code    = "LOW_QUALITY"
            )

        # ── Step 3 + 4: Hand detection & landmark completeness ────────────
        landmarks, detection_msg = self._detect_hand(frame)
        if landmarks is None:
            return ValidationResult(
                is_valid      = False,
                hand_detected = False,
                frame_valid   = True,
                landmarks     = None,
                message       = detection_msg,
                error_code    = "NO_HAND"
            )

        return ValidationResult(
            is_valid      = True,
            hand_detected = True,
            frame_valid   = True,
            landmarks     = landmarks,
            message       = "Frame valid — hand detected.",
            error_code    = "OK"
        )

    def decode_frame_only(self, frame_base64: str) -> Optional[np.ndarray]:
        """Utility: just decode without full validation (used by pipeline)."""
        return self._decode_frame(frame_base64)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _decode_frame(self, frame_base64: str) -> Optional[np.ndarray]:
        try:
            # Strip data-URI prefix if present  (data:image/jpeg;base64,...)
            if "," in frame_base64:
                frame_base64 = frame_base64.split(",", 1)[1]

            img_bytes = base64.b64decode(frame_base64)
            np_arr    = np.frombuffer(img_bytes, np.uint8)
            frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None or frame.size == 0:
                return None
            return frame
        except Exception as e:
            logger.warning(f"Frame decode failed: {e}")
            return None

    def _check_quality(self, frame: np.ndarray):
        """Check brightness — reject frames that are too dark or blank."""
        gray       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))

        if brightness < self.BRIGHTNESS_MIN:
            return False, "Frame too dark. Please improve lighting."
        if brightness > self.BRIGHTNESS_MAX:
            return False, "Frame overexposed. Please reduce lighting."
        return True, "ok"

    def _detect_hand(self, frame: np.ndarray):
        """
        Run MediaPipe hand detection.
        Returns (landmark_list, None) on success
        or (None, error_message) on failure.
        """
        try:
            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = self._mp.Image(
                image_format=self._mp.ImageFormat.SRGB,
                data=rgb
            )
            result = self._landmarker.detect(mp_image)

            if not result.hand_landmarks:
                return None, (
                    "No hand detected. Please position your hand clearly "
                    "in the centre of the camera."
                )

            landmarks = result.hand_landmarks[0]

            if len(landmarks) != 21:
                return None, (
                    "Incomplete hand landmarks. Make sure your full hand "
                    "is visible."
                )

            # Verify landmarks are within normalised bounds [0, 1]
            for lm in landmarks:
                if not (0.0 <= lm.x <= 1.0 and 0.0 <= lm.y <= 1.0):
                    return None, (
                        "Hand is partially outside the frame. "
                        "Move your hand towards the centre."
                    )

            return landmarks, None

        except Exception as e:
            logger.error(f"Hand detection error: {e}")
            return None, "Hand detection failed. Please try again."