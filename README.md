# iPhoneComposer #
==============

iPhone Composer Application for UCSD MUS270C Course

## System Requirements ##
The software has only been testing on Mac OS X, but should work on other UNIX-like operating systems. Support on Windows is not guaranteed.  The following software are required :
 - Python 2.7 or more
 - python-rtmidi python module
 - athenaCL python module
 - music21 module
 - pyosc
 - python modules can be installed using 
        	```easy_install module name```
 - touchOSC Editor and Midi Bridge both available at http://hexler.net/software/touchosc
 - iOS or Android device with the TouchOSC application installed.

## Set Up ##

Before you can use the iPhone composer, you have to upload the iPhoneComposer.touchosc layout file unto your computer and connect the device to your computer. In order to do so, follow these steps carefully : 
 + Open the layout file with the TouchOSC editor.
 + Open the Touch OSC Bridge application on your computer.
 + Make sure that the computer and the phone are on the same wifi network.
 + Once the layout file is open on the TouchOSC application, click on the "Sync" button.
 + Back on the device, open the touch OSC application. You should be seing 3 sections : Connections, Layout and Option. This is the Touch OSC Menu. 
 + Select MIDI Bridge under Connections. You should be seing your machine under Found Host() if you opened the Touch OSC Bridge app correctly. Select it and copy the IP address under Host.
 + Tap on layout > Add. You should now be seeing two (potentially empty) sections called editor hosts and found hosts. If you are lucky, the device app detects the TouchOSC editor under Found Hosts() and you just have to select the machine's name from the drop down list. Tap on Edit on the upper right corner, and then on the + on the upper left corner. Now paste the address you copied earlier here. Now you should see the address you pasted under Editor Hosts. Select it and this will upload the layout onto the TouchOSC application on your device.
 + Go back to the Touch OSC Menu and go under OSC. Paste the copied IP address under Host. Make sure that the incoming port is set to 8000 and the out coming port is set to 9000.
 + Finally, you can go back to the iPhoneComposer user interface by taping Done on your device from the TouchOSC Menu.

Now you can start the application by issuing the following command from the project's main directory:
    ```python src/main.py```
 
Once the application is started, the final set up step is to make sure that iPhone Composer is aware of your device (by this time your device should already be aware of your computer, you can make sure of this by tapping any element of the device UI, an output should appear under the OSC window on the iPhone Composer desktop application).
 + Back on the TouchOSC Menu, go under OSC and look at the Local IP Address field. 
 + Type this IP address in the Device IP Address entry on the desktop application, and enter 9000 as the Device Port (it should match with the incoming port of the device).
 + Back on the desktop application, click on Connect. This achieves the linking between the application and the device, and your iPhoneComposer is ready to be used!
 
 Note that you only need to upload the layout once, but you need to connect the desktop application to the device every time you start the application. Follow the steps.
 
 ## Notes ##
  - The last two tabs (Volume and Markov) are not yet supported. You can still edit markov weights through YAML files.
  - If markov weights are not specifically mentioned on the YAML file, some random weights are generated in order to satisy the system constraints.
  - Weights of 0 cannot be used for markov weights (it would be nice to change that in the future).
  - The save option is not yet supported.
  - The application does not support dynamic port allocation yet, so please clear the 8000 and 9000 ports on your machine in order for the machine to run properly.
 