# Hamms

Hamms is designed to elicit failures in your HTTP Client.

## Usage

1. Start hamms

    python hamms.py

2. Make requests and test your client

By default, Hamms uses ports 5500-5600. In the future this may be configurable

## Reference

### Connection level errors

Connect to the ports listed below to enact the various failure modes.

**5500** - Nothing is listening on the port
**5501** - The port accepts traffic but never sends back data
**5502** - The port sends back an empty string immediately upon connection
**5503** - The port sends back an empty string after the client sends data
**5504** - The port sends back a malformed response ("foo bar") immediately upon connection
**5505** - The port sends back a malformed response ("foo bar") after the client sends data
