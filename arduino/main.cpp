#include <Keyboard.h>

void setup()
{
    // Begin serial communication at 9600 baud rate
    Serial.begin(9600);
    // Wait for the computer to set up the connection
    while (!Serial)
    {
        ; // wait for serial port to connect. Needed for native USB
    }
    // Initialize keyboard emulation
    Keyboard.begin();
}

void loop()
{
    // Check if data is available to read from the serial port
    if (Serial.available() > 0)
    {
        String data = Serial.readStringUntil(';');
        handleKeyboardCommand(data);
    }
}

void handleKeyboardCommand(String data)
{
    // Split the data into the key and duration parts
    int separatorIndex = data.indexOf(',');
    if (separatorIndex != -1)
    {
        String keyStr = data.substring(0, separatorIndex);
        String durationStr = data.substring(separatorIndex + 1);
        int duration = durationStr.toInt();
        int modifierSepKeyStr = keyStr.indexOf('_');
        if (modifierSepKeyStr == -1)
        {
            for (int i = 0; i < keyStr.length(); i++)
            {
                Keyboard.press(keyStr.charAt(i));
            }
            delay(duration);
            Keyboard.releaseAll();
            Serial.println("1");
            return;
        }
        String keyStrVal = keyStr.substring(0, modifierSepKeyStr);
        String keyStrMod = keyStr.substring(modifierSepKeyStr + 1);
        
        int horse = 0;
        int horseSepKeyStr = keyStrMod.indexOf('^');
        int sprint = 0;
        int sprintSepKeyStr = keyStrMod.indexOf('!');
        int skill = 0;
        int skillSepKeyStr = keyStrMod.indexOf('$');

        if (horseSepKeyStr != -1) {
            horse = 1;
        }

        if (sprintSepKeyStr != -1) {
            sprint = 1;
        }

        if (skillSepKeyStr != -1) {
            skill = 1;
        }

        if (horse == 1) {
            char menuKey = 'e';
            char selectKey = KEY_DOWN_ARROW;
            Keyboard.press(menuKey);
            delay(200);
            Keyboard.press(selectKey);
            delay(100);
            Keyboard.releaseAll();
            delay(duration);
            Serial.println("1");
            return;
        }

        // skill requires use of a input device controlled by pin 8, once the pin is high the button is pressed, once the pin is low the button is released
        if(skill == 1) {
            // by default ashes of war are bound to Shift + pin 8
            Keyboard.press(KEY_LEFT_SHIFT);
            digitalWrite(8, HIGH);
            delay(duration);
            digitalWrite(8, LOW);
            Keyboard.releaseAll();
            Serial.println("1");
            return;
        }

        if (sprint == 1)
        {
            Keyboard.press(KEY_LEFT_SHIFT);
            for (int i = 0; i < keyStrVal.length(); i++) {
                Keyboard.press(keyStrVal.charAt(i));
            }
            delay(duration);
            Keyboard.releaseAll();
            Serial.println("1");
            return;
        }
    }
}