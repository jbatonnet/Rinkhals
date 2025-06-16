---
Orca Slicer Usage
---

This guide covers only the printers: Kobra 3, Kobra S1 (Combo) because only those have presets in OrcaSlicer. 

For this guide, I will use the Kobra S1.

Download and install the latest OrcaSlicer application from: [Official OrcaSlicer Repo](https://github.com/SoftFever/OrcaSlicer/releases)

!!! warning Important

    Do not use websites like "orcaslicer.net", "orcaslicer.co" or "orca-slicer.com" as those are not the official websites.

Make sure you have Rinkhals installed on your printer. 

For the installation of Rinkhals, use [this guide](../Rinkhals/installation-and-firmware-updates.md).

When you first start OrcaSlicer, you will be prompted to select a printer preset. Look for your printer and the nozzle type you are using.

![Printer Selection](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Printer-Selection.png)

Now you have a bare setup for your printer. 

We are now setting up the network service so you don’t need to use an SD card to print.

Click the **Connection** button in the printer section on the left side.

![Connection Button](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Connection.png)

Enter the local IP address of your printer and click the **Test** button.

!!! note Tip

    Ensure your printer has a static IP address configured on your router to avoid connection issues.

![Connection Settings](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Connection-Settings-Orca.png)

Leave the other fields empty.

If you see this message, you are done with setting up the network.

![Connection Successful](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Connection-OK-Orca.png)

🛠️ **Troubleshooting** 🛠️  
If you encounter this error:

![Cannot Connect Error](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Cannot-Connect-Port80-Orca.png)

Make sure your computer is connected to the same network as your printer. 
Also, ensure you are using Fluidd or Mainsail as a WebUI and have the necessary apps for those services activated.

Click **OK** on the settings screen.

Now you should be able to open the Mainsail (or Fluidd) WebUI with a click on the **Devices** tab in the upper-left corner of Orca.

![Devices Tab](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Device-Tab-Orca.png)

The WebUI should look similar to this:

![Mainsail WebUI](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Orca-Mainsail-WebUI.png)

You can now slice your prints and send them off to your printer 🖨️ 😊✌️

![Upload and Print](https://raw.githubusercontent.com/Rickeetz/Rinkhals/master/docs/docs/assets/orca-guide/Orca-Upload-and-Print.png)

You are done with setting up your printer on OrcaSlicer with the basic settings.

**Happy Printing!**
