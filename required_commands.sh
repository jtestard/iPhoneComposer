# If fundamentals are not installed
sudo apt-get update
sudo apt-get install build-essential
sudo apt-get install vim
sudo apt-get install git
sudo apt-get install binutils
sudo apt-get install python

# This should be enough.
git clone https://github.com/jtestard/iPhoneComposer.git
cd iPhoneComposer/
sudo apt-get install python-pip
sudo apt-get install python-dev
sudo easy_install pyOSC
sudo easy_install athenaCL
sudo easy_install music21
sudo easy_install python-rtmidi
sudo apt-get install libasound libasound-dev
sudo apt-get install libasound2 libasound2-dev
sudo apt-get install jackd qjackctl
sudo apt-get install libjack-dev
sudo apt-get install libjack0 libjack-dev
sudo easy_install python-rtmidi
sudo apt-get install python-tk
sudo apt-get install python-tk-dbg
sudo easy_install pyYaml
python src/main.py 
