# ORCA Xponder — simulated transponder

Stands in for the S-band MSS transponder ISRO is fitting to fishing vessels
(Nabhmitra). The satellite hop is not simulated; the terminal-to-phone link is, and
that link is real on the actual device too — the transponder pairs to the phone app
exactly like this.

What it demonstrates is the payload. A satellite message to a boat is tens of bytes,
not kilobytes, so **no sentence is ever transmitted**: the terminal sends a type code
and a wind speed, and the phone renders and speaks the warning in the fisherman's own
language. One frame is 20 bytes.

## The frame

Little-endian, 20 bytes. `firmware/esp32_xponder` and
`frontend/src/services/xponder/frame.ts` implement the same layout.

| offset | size | field |
| --- | --- | --- |
| 0 | 1 | magic, `0xA5` |
| 1 | 1 | version, `0x01` |
| 2 | 1 | message type — `1` cyclone |
| 3 | 1 | severity, 1 advisory … 4 severe |
| 4 | 4 | latitude, int32, degrees × 1e5 |
| 8 | 4 | longitude, int32, degrees × 1e5 |
| 12 | 4 | timestamp, uint32 seconds |
| 16 | 2 | wind speed, uint16 km/h |
| 18 | 2 | CRC-16/CCITT-FALSE over bytes 0–17 |

A frame that fails the magic, version or CRC check is dropped without a sound. Over a
radio link a corrupt frame is ordinary, and a cyclone warning must never be raised
from one.

## Flashing

1. Arduino IDE → Boards Manager → install **esp32** (Espressif Systems).
2. Select your board (e.g. *ESP32 Dev Module*) and its port.
3. Open `esp32_xponder/esp32_xponder.ino` and upload.
4. Tools → Serial Monitor, **115200 baud**, line ending **Newline**.

On boot it advertises as `ORCA-XPONDER`.

## Sending a cyclone warning

Type into the serial monitor and press Enter:

| command | what it sends |
| --- | --- |
| `c` | cyclone, severity 3, 95 km/h, at Digha |
| `c 4 120` | severity 4, 120 km/h |
| `c 2 60 20.26 86.69` | severity 2, 60 km/h, at Paradip |
| `h` | help |

The monitor prints the exact bytes, so you can hold them against what the phone
decoded:

```
[send] cyclone severity=3 wind=95 km/h at 21.6266, 87.5074 (20 bytes)
[frame] a5 01 01 03 ...
```

## The phone

Open ORCA and connect to `ORCA-XPONDER`. The warning takes over the screen on
whatever page is open, sounds the siren and speaks the text.

Without hardware, the same path runs in a browser: the app falls back to a simulated
terminal, and in the dev console

```js
window.orcaXponder.sendCyclone({ severity: 4, windKmh: 120 })
```

builds a real 20-byte frame and puts it through the same decoder.
