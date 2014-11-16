# Hamms

Hamms is designed to elicit failures in your HTTP Client. Connection failures,
malformed response data, slow servers, fat headers, and more!

## Installation

You can either install hamms via pip:

    pip install hamms

Or clone this project:

    git clone https://github.com/kevinburke/hamms.git

## Usage

1. Start hamms by running it from the command line:

        python hamms/__init__.py

    Or use the HammsServer class to start and stop the server on command.

    ```python
    from hamms import HammsServer

    class MyTest(object):
        def setUp(self):
            self.hs = HammsServer()
            self.hs.start()

        def tearDown(self):
            self.hs.stop()
    ```

2. Make requests and test your client. See the reference below for a list of
   supported failure modes.

By default, Hamms uses ports 5500-5600. In the future, this port range may be
configurable.

## Reference

### Connection level errors

Connect to the ports listed below to enact the various failure modes.

- **5500** - Nothing is listening on the port. Note, your machine will likely
send back a TCP reset (closing the connection) immediately.

    To simulate a connection failure that just hangs forever (a connection
    timeout), connect to a bad host on a real server, for example
    `www.google.com:81`, or use a port in the `10.*` range, for example
    `10.255.255.1`.

- **5501** - The port accepts traffic but never sends back data

- **5502** - The port sends back an empty string immediately upon connection

- **5503** - The port sends back an empty string after the client sends data

- **5504** - The port sends back a malformed response ("foo bar") immediately upon connection

- **5505** - The port sends back a malformed response ("foo bar") after the client sends data

- **5506** - The client accepts the request, and sends back one byte every 5 seconds

- **5507** - The client accepts the request, and sends back one byte every 30 seconds

- **5508** - Send a request to `localhost:5508?sleep=<float>` to sleep
for `float` number of seconds. If no value is provided, sleep for 5 seconds.

- **5509** - Send a request to `localhost:5509?status=<int>` to return
  a response with HTTP status code `status`. If no value is provided, return
  status code 200.

- **5510** - The server will send a response with a `Content-Length: 3` header,
  however the response is actually 1 MB in size

- **5511** - Send a request to `localhost:5511?size=<int>` to return a `Cookie`
  header that is `n` bytes long. By default, return a 63KB header.

- **5512** - The server keeps a counter of incoming requests. Every third
request (3, 6, 9, 12 etc) gets a 200 response; otherwise the server sends
back a 500 server error. Retrieve the count by making a GET request to
`localhost:5512/counter`. Reset the count by making a POST request to
`localhost:5512/counter`.

- **5513** - Send a request to `localhost:5513?failrate=<float>`. The server
  will drop requests with a frequency of `failrate`.

#### Not implemented yet

- The server sends back a response without a content-type
- The server sends back a response with the wrong content-type
- The server randomly drops bytes from a valid response.
- Sending back byte data

##### SSL

- Handshake timeout
- Invalid certificate
- TLS v1.0 and higher only
- TLS v1.2 and higher only
- Server closes connection
