"""Read a small cutout out of a 65 MB SPHEREx exposure without downloading the exposure.

A SPHEREx Level-2 file is laid out as PRIMARY, IMAGE, FLAGS, VARIANCE, ZODI, EPSF, WCS-WAVE.
IMAGE is plain 32-bit rows, so a cutout's rows are one contiguous byte range. FLAGS is
Rice-compressed one row per tile, with a table giving each row's byte range. The wavelength
lookup table is the file's last few kilobytes. So a cutout costs four small partial reads
(about 2 MB for a 0.15-degree view) instead of 65 MB.

This module knows nothing about HTTP: it is handed a `Source` that can read byte ranges.
"""
from __future__ import annotations

import io
import math
import struct
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from scipy.interpolate import RegularGridInterpolator

BLOCK = 2880                      # FITS files are made of 2880-byte blocks
HEAD_GUESS = 20 * BLOCK           # PRIMARY (1 block) + IMAGE header (8 blocks) with room
FLAGS_HEAD_GUESS = 14 * BLOCK     # FLAGS header (6 blocks) + its 2040-row table (6 blocks)
TAIL_GUESS = 3 * BLOCK            # WCS-WAVE: 1 header block + 1 data block


class Source(Protocol):
    """Anything that can read parts of one remote file."""

    def read(self, start: int, end: int) -> bytes:
        """Bytes start..end inclusive."""

    def tail(self, n: int) -> bytes:
        """The last n bytes."""


class NoOverlap(Exception):
    """The requested place is not inside this exposure."""


@dataclass
class RawCutout:
    """A cutout in the exposure's own pixels, exactly as NASA calibrated them."""
    image: np.ndarray             # float32 [ny, nx], MJy/sr
    flags: np.ndarray             # int32 [ny, nx], NASA's per-pixel flag bits
    wavelength: np.ndarray        # float32 [ny, nx], micron (SPHEREx's filter varies across the frame)
    header: fits.Header           # the exposure's full IMAGE header
    x0: int                       # where the cutout's first pixel sits in the full frame
    y0: int
    bytes_read: int

    @property
    def wcs(self) -> WCS:
        return cutout_wcs(self.header, self.x0, self.y0, *self.image.shape)


def cutout_wcs(header: fits.Header, x0: int, y0: int, ny: int, nx: int) -> WCS:
    """The sky mapping of a cutout whose first pixel is (x0, y0) of the full frame."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        return WCS(header, naxis=2)[y0:y0 + ny, x0:x0 + nx]


def _header_at(buf: bytes, offset: int = 0) -> tuple[fits.Header, int] | None:
    """(header, its padded length) parsed from buf[offset:], or None if its END is not in buf."""
    pos = offset
    while pos + 80 <= len(buf):
        if buf[pos:pos + 8] == b"END     ":
            length = math.ceil((pos + 80 - offset) / BLOCK) * BLOCK
            text = buf[offset:offset + length].decode("ascii", "replace")
            return fits.Header.fromstring(text), length
        pos += 80
    return None


def _padded(n: int) -> int:
    return math.ceil(n / BLOCK) * BLOCK


def _data_bytes(h: fits.Header) -> int:
    if h.get("NAXIS", 0) == 0:
        return 0
    n = abs(h["BITPIX"]) // 8
    for i in range(1, h["NAXIS"] + 1):
        n *= h[f"NAXIS{i}"]
    return n + h.get("PCOUNT", 0)


def _read_header(src: Source, offset: int, first: bytes | None, guess: int):
    """Header at `offset`, reading more if the first guess did not reach its END.
    Returns (header, padded length, bytes fetched, the buffer from offset)."""
    buf = first if first is not None else src.read(offset, offset + guess - 1)
    fetched = 0 if first is not None else len(buf)
    while True:
        got = _header_at(buf)
        if got:
            return got[0], got[1], fetched, buf
        more = src.read(offset + len(buf), offset + len(buf) + guess - 1)
        if not more:
            raise ValueError("FITS header has no END")
        fetched += len(more)
        buf += more


def _wavelength_map(tail: bytes, x0: int, y0: int, ny: int, nx: int) -> np.ndarray:
    """Wavelength (micron) of every cutout pixel, from the file's WCS-WAVE lookup table:
    a 9x9 grid of control points across the detector, interpolated bilinearly (this is what
    the header's WAVE-TAB coordinate system specifies)."""
    at = tail.rfind(b"XTENSION= 'BINTABLE'")
    if at < 0:
        raise ValueError("no wavelength table at the end of the file")
    table = fits.BinTableHDU.fromstring(tail[at:]).data
    xs = np.asarray(table["X"][0], dtype=float)        # 1-based FITS pixel coordinates
    ys = np.asarray(table["Y"][0], dtype=float)
    lam = np.asarray(table["VALUES"][0], dtype=float)[..., 0]      # [y, x]; [..., 1] is bandwidth
    interp = RegularGridInterpolator((ys, xs), lam, bounds_error=False, fill_value=None)
    yy, xx = np.mgrid[y0:y0 + ny, x0:x0 + nx]
    return interp(np.stack([yy + 1.0, xx + 1.0], axis=-1)).astype(np.float32)


def _decode_flag_rows(header: fits.Header, table: bytes, heap: bytes, heap_start: int,
                      y0: int, y1: int, width: int) -> np.ndarray:
    """Rows y0..y1 of a Rice-compressed FLAGS layer. A small valid compressed image holding
    only those rows is assembled and handed to astropy, so no private codec is used."""
    n = y1 - y0
    desc = struct.unpack(f">{2 * n}i", table[8 * y0:8 * y1])       # (length, offset) per row
    rebased = b"".join(struct.pack(">2i", desc[2 * i], desc[2 * i + 1] - heap_start)
                       for i in range(n))
    h = header.copy()
    h["NAXIS2"] = n
    h["ZNAXIS2"] = n
    h["PCOUNT"] = len(heap)
    h.remove("THEAP", ignore_missing=True)
    body = rebased + heap
    raw = (fits.PrimaryHDU().header.tostring().encode("ascii")
           + h.tostring().encode("ascii") + body + b"\0" * (_padded(len(body)) - len(body)))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with fits.open(io.BytesIO(raw)) as hl:
            data = np.asarray(hl[1].data)
    if data.shape != (n, width):
        raise ValueError(f"decoded flags have shape {data.shape}, expected {(n, width)}")
    return data.astype(np.int32)


def read_cutout(src: Source, ra: float, dec: float, half_px: int) -> RawCutout:
    """The (2*half_px+1)-pixel square around (ra, dec), clipped to the detector."""
    fetched = 0
    head = src.read(0, HEAD_GUESS - 1)
    fetched += len(head)
    primary = _header_at(head)
    if primary is None:
        raise ValueError("not a FITS file")
    image_at = primary[1] + _padded(_data_bytes(primary[0]))
    ih, ih_len, extra, _ = _read_header(src, image_at, head[image_at:], HEAD_GUESS)
    fetched += extra
    if ih.get("EXTNAME", "").strip() != "IMAGE" or ih["BITPIX"] != -32:
        raise ValueError("unexpected SPHEREx file layout: second HDU is not a float IMAGE")
    width, height = ih["NAXIS1"], ih["NAXIS2"]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        x, y = WCS(ih, naxis=2).world_to_pixel_values(ra, dec)
    if not (np.isfinite(x) and np.isfinite(y)):
        raise NoOverlap()
    cx, cy = int(round(float(x))), int(round(float(y)))
    x0, x1 = max(0, cx - half_px), min(width, cx + half_px + 1)
    y0, y1 = max(0, cy - half_px), min(height, cy + half_px + 1)
    if x1 - x0 < 3 or y1 - y0 < 3:
        raise NoOverlap()

    image_data = image_at + ih_len
    flags_at = image_data + _padded(_data_bytes(ih))
    row = width * 4

    def image_rows():
        raw = src.read(image_data + y0 * row, image_data + y1 * row - 1)
        return np.frombuffer(raw, dtype=">f4").reshape(y1 - y0, width)[:, x0:x1].astype(np.float32), len(raw)

    def flags_head():
        return _read_header(src, flags_at, None, FLAGS_HEAD_GUESS)

    def tail():
        return src.tail(TAIL_GUESS)

    with ThreadPoolExecutor(3) as pool:
        f_img, f_fl, f_tail = pool.submit(image_rows), pool.submit(flags_head), pool.submit(tail)
        (image, n_img), (fh, fh_len, n_fh, fbuf), tail_bytes = f_img.result(), f_fl.result(), f_tail.result()
    fetched += n_img + n_fh + len(tail_bytes)

    flags_data = flags_at + fh_len
    if fh.get("ZIMAGE"):                                    # Rice-compressed, one row per tile
        if (fh.get("ZTILE1"), fh.get("ZTILE2", 1)) != (width, 1) or fh["NAXIS1"] != 8:
            raise ValueError("unexpected FLAGS compression layout")
        table_len = fh["NAXIS1"] * fh["NAXIS2"]
        table = fbuf[fh_len:fh_len + table_len]
        if len(table) < table_len:
            more = src.read(flags_data + len(table), flags_data + table_len - 1)
            fetched += len(more)
            table += more
        first_len, first_off = struct.unpack(">2i", table[8 * y0:8 * y0 + 8])
        last_len, last_off = struct.unpack(">2i", table[8 * (y1 - 1):8 * y1])
        heap_at = flags_data + fh.get("THEAP", table_len)
        heap = src.read(heap_at + first_off, heap_at + last_off + last_len - 1)
        fetched += len(heap)
        flags = _decode_flag_rows(fh, table, heap, first_off, y0, y1, width)[:, x0:x1]
    else:                                                   # a plain integer image
        dtype = {32: ">i4", 16: ">i2", 8: "u1", 64: ">i8"}[fh["BITPIX"]]
        frow = width * abs(fh["BITPIX"]) // 8
        raw = src.read(flags_data + y0 * frow, flags_data + y1 * frow - 1)
        fetched += len(raw)
        flags = np.frombuffer(raw, dtype=dtype).reshape(y1 - y0, width)[:, x0:x1].astype(np.int32)

    wavelength = _wavelength_map(tail_bytes, x0, y0, y1 - y0, x1 - x0)
    return RawCutout(image=image, flags=np.ascontiguousarray(flags), wavelength=wavelength,
                     header=ih, x0=x0, y0=y0, bytes_read=fetched)
