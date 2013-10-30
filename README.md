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

- **5500** - Nothing is listening on the port. Note, your machine will send
back a TCP reset (closing the connection) immediately. To simulate a connection
failure that just hangs forever, connect to a bad host on a real server, for
example `www.google.com:81`, or use a port in the `10.*` range, for example
`10.255.255.1`.

- **5501** - The port accepts traffic but never sends back data

- **5502** - The port sends back an empty string immediately upon connection

- **5503** - The port sends back an empty string after the client sends data

- **5504** - The port sends back a malformed response ("foo bar") immediately upon connection

- **5505** - The port sends back a malformed response ("foo bar") after the client sends data

- **5506** - The client accepts the request, and sends back one byte every 5 seconds

- **5507** - The client accepts the request, and sends back one byte every 30 seconds

#### Not implemented yet

- The server sends a full HTTP response, then sends back more data
- The server sends back a response without a content-type
- The server sends back a response with the wrong content-type
- The server randomly drops bytes from a valid response.
- The server will drop 1 out of every 10 requests
- The server will drop 1 out of every 100 requests
- The server sends back 1 MB worth of headers
- The server sends back 10 MB worth of headers
- The server sends a response after 5 seconds
- The server sends a response after 30 seconds
- The server sends a response after 2 minutes
