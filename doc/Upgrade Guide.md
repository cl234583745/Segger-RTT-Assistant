**English | [简体中文](升级指南.md)**
# RTT Assistant - Upgrade Guide


## 1. Upgrade Risk Warning
    Upgrading carries risks; you are responsible for manual upgrades

## 2. How to Upgrade the JLink Version

### Directly Replace the DLL File

This is the simplest method; no need to reinstall the JLink software.

**Steps**:

1. **Download the New JLink Version**
   - Visit: https://www.segger.com/downloads/jlink/
   - Download the latest version of the JLink software

2. **Extract the DLL File**
   - Install or extract the JLink software
   - Locate the DLL file:
     - 64-bit: `JLink_x64.dll`
     - 32-bit: `JLinkARM.dll`
   - Typically located at: `C:\Program Files\SEGGER\JLink_V9xx\`

3. **Replace the DLL**
   - Copy the new DLL file to the RTT Assistant directory
   - Replace the old `JLink_x64.dll` file
   - Restart RTT Assistant

**Notes**:
- Ensure the DLL bitness matches the Python bitness
- 64-bit Python uses `JLink_x64.dll`
- 32-bit Python uses `JLinkARM.dll`
- **Only 64-bit systems have been verified so far**


## 3. Python and Other Dependency Upgrades
    About - Dependency Management: You can view the related dependencies, click the upgrade button, or manually replace the files in the relevant folders