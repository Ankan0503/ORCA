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
| 2 | 1 | message type — `1` cyclone, `2` lightning, `0x10` SOS, `0x11` SOS received |
| 3 | 1 | severity — storm strength down, nature of the emergency up |
| 4 | 4 | latitude, int32, degrees × 1e5 |
| 8 | 4 | longitude, int32, degrees × 1e5 |
| 12 | 4 | timestamp, uint32 seconds |
| 16 | 2 | read by type: wind km/h, minutes until lightning, or people aboard |
| 18 | 2 | CRC-16/CCITT-FALSE over bytes 0–17 |

The same twenty bytes carry a distress call as carry a warning: only the meaning of
`severity` and `value` changes with the type. Nothing had to grow to make the link
two-way, which is the point of sending codes rather than words.

| severity | as a storm | as an SOS |
| --- | --- | --- |
| 1 | advisory | medical emergency |
| 2 | watch | engine failure |
| 3 | warning | man overboard |
| 4 | severe | boat sinking |

A frame that fails the magic, version or CRC check is dropped without a sound. Over a
radio link a corrupt frame is ordinary, and neither a cyclone warning nor a distress
call must ever be raised from one.

## Characteristics

Service `0xA5C1`, advertised as a 16-bit UUID so the packet stays inside its 31 bytes.

| characteristic | direction | properties |
| --- | --- | --- |
| `0xA5C2` downlink | terminal → phone | notify, read |
| `0xA5C3` uplink | phone → terminal | write |

## Flashing

1. Arduino IDE → Boards Manager → install **esp32** (Espressif Systems).
2. Select your board (e.g. *ESP32 Dev Module*) and its port.
3. Open `esp32_xponder/esp32_xponder.ino` and upload.
4. Tools → Serial Monitor, **115200 baud**, line ending **Newline**.

On boot it advertises as `ORCA-XPONDER`.

## Sending a warning

Type into the serial monitor and press Enter:

| command | what it sends |
| --- | --- |
| `c` | cyclone, severity 3, 95 km/h, at Digha |
| `c 4 120` | cyclone, severity 4, 120 km/h |
| `c 2 60 20.26 86.69` | cyclone, severity 2, 60 km/h, at Paradip |
| `l` | lightning, severity 3, 40 minutes away |
| `l 4 15` | lightning, severity 4, 15 minutes away |
| `l 4 15 20.26 86.69` | ... at Paradip |
| `h` | help |

Lightning has its own type code because it kills more Indian fishermen than cyclones
do — a cyclone is seen coming for days, a thunderstorm is not, and an open boat has no
shelter from it. The action it calls for is different too: not *"do not go out"* but
*"come back now"*. It cost **no extra bytes** — a second type code, and the sentences
it becomes live on the phone.

The monitor prints the exact bytes, so you can hold them against what the phone
decoded:

```
[send] cyclone severity=3 wind=95 km/h at 21.6266, 87.5074 (20 bytes)
[frame] a5 01 01 03 ...
```

## Receiving an SOS

The link runs both ways. On the phone, open **Is it safe? → SOS**, choose what is
wrong, set how many people are aboard, and hold the button for two seconds. The phone
reads its GPS, builds the same 20-byte frame, and writes it to the terminal.

There is no S-band transmitter on an ESP32, so the serial monitor stands in for the
coastguard's receiver:

```
[recv] a5 01 10 03 20 00 21 00 c6 86 85 00 9a 8e a5 6a 04 00 3d a1
[SOS ] ================ DISTRESS CALL ================
[SOS ] MAN OVERBOARD
[SOS ] position 21.62720, 87.50790
[SOS ] 4 people on board
[SOS ] >>> would transmit on S-band to the coastguard <<<
```

The terminal then acknowledges back down the link — the phone changes from *"Sent —
waiting for the transponder"* to *"Transponder has your message"* — and buzzes and
blinks, so the boat knows even if the phone is flat. Wire a buzzer to **GPIO 4** for the
noise; the LED is on whatever `LED_BUILTIN` your board defines.

That acknowledgement means exactly one thing: the terminal holds the bytes. Whether a
coastguard has read them is not something an ESP32 can know, so nothing claims it.

Holding for two seconds is deliberate: the only thing worse than an SOS that will not
send is one that sends from a pocket.

## The phone

Open ORCA and connect to `ORCA-XPONDER`. The warning takes over the screen on
whatever page is open, sounds the siren and speaks the text.

Without hardware, the same path runs in a browser: the app falls back to a simulated
terminal, and in the dev console

```js
window.orcaXponder.sendCyclone({ severity: 4, windKmh: 120 })
```

builds a real 20-byte frame and puts it through the same decoder.
