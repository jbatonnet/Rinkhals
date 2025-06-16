---
title: Add 3rd Party Webcams into Mainsail
---

⚠️ **This is Experimental! No support will be provided!** Expect performance degradations while using third-party webcams on your machine. ⚠️  
The machine will most likely only accept USB webcams that do not require additional drivers.

Tested Webcams:

- EMEET Full HD Webcam - C960 1080P ✅

### Adding a USB Webcam to Mainsail

1. **Connect your webcam via USB to the printer.**

    ![USB Connection](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/webcam-guide/USB-Webcam%20Connect.jpg)

2. **Reboot the printer** after connecting the cable.

3. **SSH into the machine** using the standard credentials:

    ```
    User: root
    Pass: rockchip
    ```

4. Use the command `dmesg | grep -i usb` to check if your webcam is initialized.

    You should see a list of connected USB devices. Look for the vendor of your webcam. In my case, it is Deepstech.

    ![SSH USB DMESG](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/webcam-guide/Deepstech-Webcam-Init.png)

### Configuring the Webcam in Mainsail

1. Open the **Device Tab** in OrcaSlicer.

    ![Devices Tab](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Device-Tab-Orca.png)

2. Access your **Mainsail WebUI**, which should look similar to this:

    ![Mainsail WebUI](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Orca-Mainsail-WebUI.png)

3. Click the **Settings Icon** in the Mainsail UI and scroll down to the **Webcam Section**.

    ![Mainsail Webcam Settings](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/webcam-guide/Mainsail-Webcam-Settings-URL.png)

4. You will see the printer's internal webcam. Update the URLs for the Webcam Stream and Snapshot functions.  
    `/webcam/` is always the internal webcam. Try `/webcam1/`, and if that doesn't work, increment the number up to `/webcam3/`.

    Eventually, you should see the webcam feed from the connected USB webcam, which will look like this:

    ![Mainsail Webcam Settings USB Cam](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/webcam-guide/Mainsail-Webcam-Settings-USB-Cam.png)

5. Use the **"Adaptive MJPEG-Streamer (experimental)"** service and click **"Save Webcam"**.

6. Switch to your **Dashboard** and set the webcams to "All." You should now see both webcams working.

!!! note
    
    **Do not use the stream option!** It will spike your CPU usage. ⚠️


🎉 You have successfully added a webcam! Happy Printing! 😃
