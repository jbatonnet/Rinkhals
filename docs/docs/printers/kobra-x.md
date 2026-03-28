---
title: Anycubic Kobra X (K4Pro)
---

## General

- **Software base**: `KlipperC++`
- **Supported by Rinkhals**: `No` (Blocked by RSA Signature)
- **Firmware SWU password**: `rCRgz7RMqOyAYCaQ7TgkmPPDyo3LIEqtuEhv8ZEASa7rfwP3p2XoyQZA8IYYV8W3`
- **MCU SWU password**: `U2FsdGVkX19deTfqpXHZnB5GeyQ/dtlbHjkUnwgCi+w=`
- **Ex/Im password**: `2YLVrATRvUEnMeXk6Vtc7qxfzYM4TJzrLnEBma8zpUKeGtseGWqp4LXs7e8KeU2u`
- **SSH root password**: `rockchip`

*Thanks to AndrewS for the system dump and Ac_K for passwords and technical discovery.*

## Software Architecture

The Kobra X (K4 software base) represents a complete overhaul compared to the K3 series. It moves away from the Go-based "GoKlipper" stack (K3SysUi, gklib, gkapi) and introduces a C++ implementation of Klipper.

The core system processes are:
- **avata_main**: The main control logic (C++ Klipper port).
- **avata_ui**: The user interface.
- **avata_video**: The cam control logic.

## Firmware Security & RSA Barrier

The Kobra X introduces mandatory **RSA Signature Verification**. The installer validates the update package (setup.tar.gz) against a public key (/etc/ssl/public_key.pem) using OpenSSL.

Because the setup.tar.gz must be signed by Anycubic's private key to generate a valid setup.sig file, custom firmware injection is currently impossible through standard update methods.

## Potential Bypass and Risks

Future custom firmware installation will require a vulnerability to bypass this check, such as:

1. Physical Access: Using Serial to gain root access and manually overwrite the public key.
2. Software Vulnerabilities: Finding a flaw in the avata_main or avata_ui processes to achieve arbitrary code execution.

### Stability and Update Warnings
If a bypass is found and a custom firmware is installed, be aware of the following:

- **OTA Updates**: Over-the-air updates will no longer function.
- **Manual Updates**: Installing an official firmware file will overwrite the custom firmware and could lead to a system mismatch.
- **Brick Risk**: Mixing official update components with modified system files carries a significant risk of "bricking" the printer, potentially making it unbootable (Recoverable by Serial).
