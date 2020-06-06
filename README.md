# Python Android SDK Manager

This is a project I worked on because I was attempting to get the developer Android Emulator up and running without having Android Studio, however faced issues with downloading the latest versions of the Emulator, and the Google Play Store supporting images, due to, at least on Windows, the SDK Manager tool included with the [Commandline tools](https://developer.android.com/studio#command-tools) not supporting the '--channel=3' operator to allow downloading of the latest versions.

# Pre-requisites
I tried to make this as lightweight as possible to have minimal prerequisites:
- Python 3.6.8

That's the earliest version I've tested this on, but I believe this may work back to 3.3. If anyone tests that, let me know.

# Usage
Make sure you have the `ANDROID_SDK_ROOT` or `ANDROID_SDK_HOME` environment variables set, otherwise the download tool will fail not knowing where to download things to.

Once set up, inside the cloned repo, just run `python downloadtools.py [packages]` and it will download the latest version of that package available.
Or run `python downloadtools.py` to list raw package names. (Do note this lists *ALL* packages, including Google-deemed 'obsolete' ones)

# Notes
This does not support installing HAXM or Glass repos, or other binary style installs. I would recommend just using this tool to install commandline tools to then set that up.
The main goal of this is to give an alternative downloader when the SDK manager included doesn't work correctly, without needing to dig through XML files yourself.
