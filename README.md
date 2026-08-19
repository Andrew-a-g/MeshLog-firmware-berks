# MeshLog firmware for BerksMesh

Firmware for a [MeshCore logger](https://github.com/Anrijs/MeshLog), maintained as a BerksMesh-specific fork.

> **Release status:** use the assets attached to the latest tagged GitHub Release for supported, hardware-validated downloads. Ordinary CI artifacts remain **unvalidated development outputs** and must not be recommended.

## BerksMesh radio profile

All board environments inherit this profile from `platformio.ini`:

| Setting | Value |
|---|---:|
| Frequency | **869.618 MHz** |
| Bandwidth | **62.5 kHz** |
| Spreading factor | **8** |
| Coding rate | **4/8** (`LORA_CR=8`) |

The firmware retains upstream's built-in `Public` channel. Its PSK is embedded in public source code and is a shared interoperability value, **not** a confidential credential or proof of identity. A proposed patch that appended `#berks`, `#berksbot`, and `#jokes` at every boot is intentionally omitted from this release preparation: the current channel API does not establish that doing so can preserve a full or customized persisted channel list. Add those public/community channels through the CLI after commissioning until a separately reviewed migration exists. Confirm that this radio profile is legal for the operating location and hardware before transmitting.

## Configured build targets

These PlatformIO environments are configured and included in the candidate matrix. “Configured” does not mean compiled successfully, and a successful compile does not mean physically supported. CI logs and a candidate manifest provide compile evidence; only release notes with per-checksum physical test records may claim physical support.

| Hardware | Environment |
|---|---|
| Generic E22 (ESP32) | `Generic_E22_meshlog` |
| Heltec WiFi LoRa 32 V3 | `Heltec_lora32_v3_meshlog` |
| Heltec WiFi LoRa 32 V4 | `Heltec_v4_meshlog` |
| LilyGo T3-S3 | `LilyGo_T3S3_meshlog` |
| LilyGo T-LoRa V2.1 | `LilyGo_TLora_v2_1_meshlog` |
| Seeed XIAO ESP32-S3 + Wio-SX1262 | `Xiao_S3_meshlog` |

Heltec V2 work exists separately on the local assessment branch and is deliberately not in the release matrix because it has not been accepted or physically validated.

## Development candidate build

Use Python 3.11 and the same pinned PlatformIO Core as CI:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install platformio==6.1.18
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
pio run -e Heltec_lora32_v3_meshlog -t mergebin
```

`SOURCE_DATE_EPOCH` reduces time-derived variation in compiler strings, and direct dependencies/platforms are pinned in `platformio.ini`. These controls improve repeatability but do not guarantee bit-for-bit reproducibility across hosts or transitive tool changes. The PlatformIO pre-script refuses a dirty tree and records the full `HEAD`, environment, and epoch beside every build. A merged image is written to `.pio/build/<environment>/firmware-merged.bin`. Build all six environments before packaging.

Run tests and package the existing build outputs:

```sh
python -m unittest discover -s tests -v
for env in Generic_E22_meshlog Heltec_lora32_v3_meshlog Heltec_v4_meshlog \
  LilyGo_T3S3_meshlog LilyGo_TLora_v2_1_meshlog Xiao_S3_meshlog; do
  pio run -e "$env" -t mergebin
done
python scripts/package_release.py \
  --version "1.5.0-dev.$(git rev-parse HEAD)" \
  --commit "$(git rev-parse HEAD)" \
  --source-date-epoch "$SOURCE_DATE_EPOCH" \
  --output dist
(cd dist && sha256sum --check SHA256SUMS)
```

Packaging requires the full supplied commit to equal a clean checkout's `HEAD`, and requires matching clean-build provenance from every environment. The output path must not already exist; the packager never recursively replaces a caller-selected directory. The bundle contains one board-specific merged `.bin`, `manifest.json`, and `SHA256SUMS`; the checksum file covers the manifest as well as every image. The manifest intentionally says `UNVALIDATED`. GitHub Actions uses a commit-unique development version and only uploads short-lived CI artifacts; it does not create a GitHub Release.

## Flashing a merged image

1. Match the board label and PlatformIO environment exactly. A wrong image can fail to boot and may use incorrect radio pins.
2. Verify the download from the bundle directory: `sha256sum --check SHA256SUMS`.
3. Connect the board by USB, identify its serial port, and put it in bootloader mode if its board documentation requires it.
4. Install the pinned tooling in the virtual environment above.
5. Erase and flash the **merged** image at offset `0x0`:

   ```sh
   pio pkg exec --package "tool-esptoolpy" -- esptool.py \
     --chip auto --port /dev/ttyUSB0 erase_flash
   pio pkg exec --package "tool-esptoolpy" -- esptool.py \
     --chip auto --port /dev/ttyUSB0 --baud 460800 write_flash 0x0 \
     dist/meshlog-berks-<version>-<board>-merged.bin
   ```

   On some systems the port is `/dev/ttyACM0`; on Windows it is a `COM` port. Reduce the baud rate if flashing is unreliable.
6. Reboot and monitor at 115200 baud: `pio device monitor --port /dev/ttyUSB0 --baud 115200`.

Flashing erases existing configuration and identity. Private-key **export is not compiled into the release-matrix environments** because serial export can turn physical/console access into identity compromise; import remains enabled for deliberate recovery. Before erasing, use an already secured backup or a separately reviewed migration procedure rather than weakening a distributable candidate. Treat any exported key as the node identity, store it encrypted with restricted access, and never paste it into logs, chat, or issue reports. Likewise, never expose non-public channel PSKs, Wi-Fi credentials, or logger authentication secrets.

## Initial logger configuration

Connect to the firmware CLI over serial and enter values appropriate to the installation:

```text
log url https://<your-site>/meshlog/log.php
log report 1800
log auth <unique-secret>
wifi ssid <ssid>
wifi password <password>
set name <node-name>
set lat <latitude>
set lon <longitude>
reboot
```

`log report 0` disables self-reports. Use HTTPS and a unique authentication secret. After reboot, verify Wi-Fi association, logger delivery, node identity/location, channel presence, and radio traffic with another known-good BerksMesh node. Do not claim successful support based on compilation alone.

See [docs/RELEASING.md](docs/RELEASING.md) for validation, release, rollback, and support requirements.
