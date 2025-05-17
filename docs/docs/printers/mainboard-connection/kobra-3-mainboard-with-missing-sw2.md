---
title: Kobra 3 mainboard with missing SW2
---

![](../../assets/mainboard-connection/kobra-3-mainboard-with-missing-sw2/kobra-3-mainboard-with-missing-sw2-1.webp)

![](../../assets/mainboard-connection/kobra-3-mainboard-with-missing-sw2/kobra-3-mainboard-with-missing-sw2-2.webp)

So down is GND, up is 5V in the picture

The opposite of yours, but maybe that's it for the K3M

Do you have labels on the back?

Anyway I guess there are some diodes to block reverse current..

![](../../assets/mainboard-connection/kobra-3-mainboard-with-missing-sw2/kobra-3-mainboard-with-missing-sw2-3.webp)

This is my setup, the USB-C cable is already plugged to my laptop

![](../../assets/mainboard-connection/kobra-3-mainboard-with-missing-sw2/kobra-3-mainboard-with-missing-sw2-4.webp)

`dmesg -w` on the left and `lsusb` on the right 

![](../../assets/mainboard-connection/kobra-3-mainboard-with-missing-sw2/kobra-3-mainboard-with-missing-sw2-5.webp)

If I just plug the board without SW2, the LED goes red and after a few seconds I hear 2 beeps (cause it boots)

Nothing on the laptop

![](../../assets/mainboard-connection/kobra-3-mainboard-with-missing-sw2/kobra-3-mainboard-with-missing-sw2-6.webp)

Okay, then I use a USB drive (why not..) to short SW2

While I plug the USB JST connector

This time it did not work, so I guess I plugged the USB-C in reverse

![](../../assets/mainboard-connection/kobra-3-mainboard-with-missing-sw2/kobra-3-mainboard-with-missing-sw2-8.webp)

Ok that was it, USB in reverse, so I reversed the USB-C connector

Now the laptop displays errors in dmesg

As soon as the cable was connected, maybe 1s after connection

![](../../assets/mainboard-connection/kobra-3-mainboard-with-missing-sw2/
kobra-3-mainboard-with-missing-sw2-9.webp)

Okay finally got it, after a couple of retries / reversing cable / changing cable

You see 3 lines on the left with New USB found

And the Fuzhou Rockchip on the right