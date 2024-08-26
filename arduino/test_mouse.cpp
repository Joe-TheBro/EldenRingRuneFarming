int switchPin = 8; // Pin connected to the base of the transistor

void setup()
{
    pinMode(switchPin, OUTPUT);
    digitalWrite(switchPin, LOW); // Start with the switch off
}

void loop()
{
    // To connect the two points
    digitalWrite(switchPin, HIGH);
    delay(1000); // Keep them connected for 1 second

    // To disconnect the two points
    digitalWrite(switchPin, LOW);
    delay(1000); // Keep them disconnected for 1 second
}
