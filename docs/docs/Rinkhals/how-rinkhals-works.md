---
title: How does Rinkhals work?
---

Rinkhals is a robust custom firmware extension (overlay) designed specifically for Anycubic Kobra 3D printers running the proprietary "Kobra OS" stack. 

Instead of completely erasing the printer to install vanilla Klipper (which usually breaks the native touchscreen UI and Anycubic cloud integrations), Rinkhals is built to safely run *alongside* the stock environment. This gives you the best of both worlds: open-source community features combined with the polished aspects of the stock firmware.

## How it modifies the stock firmware

1. **System Injection via SWU:**
   Instead of flashing a raw bin file over serial, Rinkhals exploits the native Anycubic `.swu` update mechanism. By placing the payload in a specific `aGVscF9zb3Nf` folder on a USB stick, the system accepts the Rinkhals package and overlays it onto the internal Linux filesystem on top of the original firmware.
   
2. **Daemon & Boot Script Interception:**
   When the printer boots, Rinkhals safely intercepts the standard startup scripts. It ensures that its own underlying services (like network modifications and the app ecosystem) start simultaneously with Anycubic's `gklib` (their Go lang port of Klipper) and `gkapi` infrastructure without creating conflicts.

3. **Dynamic UI Binary Patching:**
   The most visible modification is on the Kobra Touchscreen. Rinkhals dynamically patches the machine's closed-source UI binary (`K3SysUi`) to inject a custom touch menu. By selectively overriding the stock "Support" button in the settings, it embeds its own App Manager and system controls directly onto the Anycubic screen.

4. **Unlocking SSH & Permissions:**
   Out of the box, the Anycubic OS is heavily locked down. The modification roots the underlying Linux environment (via the Rockchip chipset) and opens standard SSH access to port 22 natively.

## What Rinkhals Provides

By bridging the gap between walled-garden firmware and the open-source Klipper community, Rinkhals enriches the printer with:

- **Industry-Standard Web Interfaces:** Full support for running Moonraker, allowing you to use modern responsive interfaces like **Mainsail** and **Fluidd**.
- **On-Screen Slicer Integration:** Full integration allowing slicing engines like **Orca Slicer** to send jobs directly over the local network via Moonraker, complete with automatic print thumbnails shown natively on the Kobra's screen.
- **Hardware Extensions:** Enables universal USB camera support inside the web interfaces for remote monitoring.
- **Rinkhals Touch UI & OTA:** The patched printer screen gives you a "Rinkhals" dashboard. You can install Over-The-Air updates without USB drives, restart services, and manage your printer straight from the display.
- **App Ecosystem:** A highly optimized plugin marketplace specifically for weak CPUs. Allows you to easily click-to-install packages like Tailscale, Cloudflare deployment tools, OctoApp Companions, and more.
