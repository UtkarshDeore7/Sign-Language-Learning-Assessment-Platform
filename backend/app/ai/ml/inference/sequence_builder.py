import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import Optional

@dataclass
class SequenceResult:
    sequence: np.ndarray      # Shape: (N, 63)
    frame_count: int
    is_ready: bool            # True when buffer has N frames
    buffer_size: int

class FrameBuffer:
    """
    Stores last N frames of landmark vectors.
    Prepares data structure for future LSTM/GRU models.
    """
    def __init__(self, buffer_size: int = 20):
        self.buffer_size = buffer_size
        self.buffer = deque(maxlen=buffer_size)

    def add_frame(self, landmark_vector: np.ndarray):
        """Add a 63-value landmark vector to buffer"""
        if len(landmark_vector) != 63:
            raise ValueError(f"Expected 63 features, got {len(landmark_vector)}")
        self.buffer.append(landmark_vector.copy())

    def is_ready(self) -> bool:
        """True when buffer has enough frames"""
        return len(self.buffer) == self.buffer_size

    def get_sequence(self) -> Optional[np.ndarray]:
        """Returns sequence tensor of shape (N, 63)"""
        if not self.is_ready():
            return None
        return np.array(list(self.buffer))

    def clear(self):
        self.buffer.clear()

    def current_size(self) -> int:
        return len(self.buffer)


class SequenceBuilder:
    """
    Converts individual landmark frames into
    sequences suitable for temporal models (LSTM/GRU).
    """
    def __init__(self, sequence_length: int = 20):
        self.sequence_length = sequence_length
        self.buffer = FrameBuffer(buffer_size=sequence_length)

    def add_frame(self, landmark_vector: np.ndarray) -> SequenceResult:
        """
        Add one frame and return current sequence status.
        Input: 63-value landmark vector
        Output: SequenceResult with tensor if ready
        """
        self.buffer.add_frame(landmark_vector)
        sequence = self.buffer.get_sequence()

        return SequenceResult(
            sequence=sequence if sequence is not None else np.array([]),
            frame_count=self.buffer.current_size(),
            is_ready=self.buffer.is_ready(),
            buffer_size=self.sequence_length
        )

    def reset(self):
        self.buffer.clear()

    def get_tensor_shape(self) -> tuple:
        """Returns expected tensor shape for sequence model"""
        return (self.sequence_length, 63)


def demo_sequence_builder():
    """Demo showing how sequence builder works"""
    print("Sequence Builder Demo")
    print(f"Buffer size: 20 frames x 63 features = (20, 63) tensor\n")

    builder = SequenceBuilder(sequence_length=20)

    # Simulate 25 frames coming in from webcam
    for i in range(25):
        # Simulate a 63-value landmark vector
        fake_landmarks = np.random.rand(63)
        result = builder.add_frame(fake_landmarks)

        if result.is_ready:
            print(f"Frame {i+1}: Buffer READY | Shape: {result.sequence.shape}")
        else:
            print(f"Frame {i+1}: Buffering... ({result.frame_count}/{result.buffer_size})")

    print(f"\nFinal tensor shape: {builder.get_tensor_shape()}")
    print("This tensor is ready to be passed to LSTM/GRU in the future.")

if __name__ == "__main__":
    demo_sequence_builder()