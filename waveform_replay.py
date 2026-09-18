"""Offline complex-IQ diagnostics. No device access, classification or label inference."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np

MAX_BYTES = 20 * 1024 * 1024
MAX_SAMPLES = 1000000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def diagnostics(x):
    """Complex FFT after DC removal; frequency is cycles/sample, never inferred Hz."""
    x = x.astype(np.complex128)
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        amplitude = np.abs(x)
        peak = float(amplitude.max())
        rms = float(peak * np.sqrt(np.mean((amplitude / peak)**2))) if peak else 0.0
        mean = x.mean()
        centered = x - mean
        scale = float(np.abs(centered).max())
        if scale:
            power = np.abs(np.fft.fft(centered / scale))**2
            index = int(np.argmax(power))
            fraction = float(power[index] / power.sum())
            frequency = float(np.fft.fftfreq(len(x))[index])
        else:
            fraction, frequency = 0.0, None
        result = {'rms': rms, 'peak': peak, 'mean_i': float(mean.real),
                  'mean_q': float(mean.imag), 'dominant_ac_cycles_per_sample': frequency,
                  'dominant_ac_energy_fraction': fraction}
    if not all(value is None or np.isfinite(value) for value in result.values()):
        raise ValueError('Derived diagnostics overflowed; input is unsupported')
    return result


def replay_bytes(blob, window_size=128):
    if type(window_size) is not int or not 2 <= window_size <= 65536:
        raise ValueError('Invalid window size')
    if not isinstance(blob, bytes) or len(blob) > MAX_BYTES:
        raise ValueError('Invalid or oversized file')
    stream = io.BytesIO(blob)
    version = np.lib.format.read_magic(stream)
    readers = {(1, 0): np.lib.format.read_array_header_1_0,
               (2, 0): np.lib.format.read_array_header_2_0}
    if version not in readers:
        raise ValueError('Unsupported NPY format')
    shape, _, dtype = readers[version](stream)
    if len(shape) != 1 or dtype.kind != 'c' or dtype.itemsize not in (8, 16):
        raise ValueError('Expected one-dimensional complex64/complex128 IQ')
    if not 1 <= shape[0] <= MAX_SAMPLES:
        raise ValueError('Unsupported declared sample count')
    if len(blob) - stream.tell() != shape[0] * dtype.itemsize:
        raise ValueError('Truncated or trailing array payload')
    x = np.load(io.BytesIO(blob), allow_pickle=False)
    if not np.isfinite(x).all():
        raise ValueError('Invalid sample count or nonfinite IQ')
    windows = []
    for start in range(0, len(x), window_size):
        part = x[start:start + window_size]
        windows.append({'start': start, 'sample_count': len(part),
                        'partial': len(part) < window_size, **diagnostics(part)})
    result = {'scope': 'Saved complex-IQ diagnostics only; no anomaly verdict or external accuracy',
              'source_sha256': hashlib.sha256(blob).hexdigest(), 'dtype': str(x.dtype),
              'sample_count': len(x), 'window_size': window_size,
              'sample_rate_hz': None, 'center_frequency_hz': None,
              'amplitude_units': 'Unverified stored array units', 'samples_dropped': 0,
              'resampled': False, 'iq_components_preserved': True,
              'source_summary': diagnostics(x), 'windows': windows}
    result['diagnostic_sha256'] = hashlib.sha256(canonical(result)).hexdigest()
    return result


def read_bounded(path):
    with Path(path).open('rb') as stream:
        blob = stream.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise ValueError('Oversized source file')
    return blob


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--window-size', type=int, default=128)
    args = parser.parse_args()
    result = replay_bytes(read_bounded(args.source), args.window_size)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
