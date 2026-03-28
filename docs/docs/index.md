---
title: Home
weight: -1
hide:
  - navigation
---

## Overview

Welcome to the Rinkhals project documentation!

Rinkhals is a custom firmware overlay for the Anycubic Kobra series of 3D printers. It supports Kobra 2 Pro, Kobra 3 series, and Kobra S1 series.
This documentation covers what we know about those printers, the Anycubic software stack, Rinkhals internals, and high-level guides to achieve specific goals.

## Support Status

### Supported Models (GoKlipper / K3)
These printers are currently compatible with Rinkhals:
- **K2P**: [Anycubic Kobra 2 Pro](printers/kobra-2-pro.md)
- **K3**: [Anycubic Kobra 3](printers/kobra-3.md) (+ Combo)
- **K3V2**: [Anycubic Kobra 3 V2](printers/kobra-3-v2.md) (+ Combo)
- **K3M**: [Anycubic Kobra 3 Max](printers/kobra-3-max.md) (+ Combo)
- **KS1**: [Anycubic Kobra S1](printers/kobra-s1.md) (+ Combo)
- **KS1M**: [Anycubic Kobra S1 Max](printers/kobra-s1-max.md) (+ Combo)

### Experimental / Incompatible (KlipperC++ / K4)
- **K4Pro**: [Anycubic Kobra X](printers/kobra-x.md) — Currently **not supported** due to RSA signature verification.

---

## Getting Started

The main project is located on GitHub: [https://github.com/jbatonnet/Rinkhals](https://github.com/jbatonnet/Rinkhals)<br />
To quickly start using Rinkhals, check the [quick start guide](guides/rinkhals-quick-start.md)

If you prefer a video, [Kanrog](https://www.youtube.com/@kanrogcreations) on Discord made a video explaining how to install Rinkhals:

<p align="center">
    <iframe width="480" height="270" src="https://www.youtube.com/embed/2CfgHLggjOA?si=uppWjupqwzUq7hmm" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

    <iframe width="480" height="270" src="https://www.youtube.com/embed/1VpJGZLuQyI?si=lekaw1rFgSfZ6vvT" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
</p>

## Documentation Structure

- [Rinkhals](Rinkhals/index.md): Documentation about Rinkhals, its features and internals.
- [Guides](guides/index.md): High level guides for Simplyprint, Spoolman, and more.
- [Printers](printers/index.md): Generic and specific documentation about the Anycubic Kobra series.
- [Firmware](firmware/index.md): Reverse engineering and documentation about the original firmware.

## FAQ

Please check the [FAQ](faq.md) for commonly asked questions about Rinkhals.

## Useful Links

- Rinkhals repository: [https://github.com/jbatonnet/Rinkhals](https://github.com/jbatonnet/Rinkhals)
- Rinkhals apps repository: [https://github.com/jbatonnet/Rinkhals.apps](https://github.com/jbatonnet/Rinkhals.apps)