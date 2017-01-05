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

        python -m hamms

    Or use the HammsServer class to start and stop the server on command.

    ```python
    from hamms import HammsServer

    class MyTest(object):
        def setUp(self):
            self.hs = HammsServer()
            self.hs.start(beginning_port=5500)

        def tearDown(self):
            self.hs.stop()
    ```

2. Make requests and test your client. See the reference below for a list of
   supported failure modes.

By default, Hamms uses ports 5500-5600. You can customize the port range by
passing the `beginning_port` parameter to `HammsServer.start()`.

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
  however the response is actually 1 MB in size. This can break clients that
  reuse a socket.

- **5511** - Send a request to `localhost:5511?size=<int>` to return a `Cookie`
  header that is `n` bytes long. By default, return a 63KB header. 1KB larger
  will break many popular clients (curl, requests, for example)

- **5512** - Use this port to test retry logic in your client - to ensure that
it retries on failure.

    The server maintains a counter for incoming requests. Each time a new
    request is made, a 500 error is served and the counter is decremented. When
    the counter reaches zero, a 200 response is served. This server accepts two
    query arguments:

    - **key** - Specify a `key` to create a new counter. Continue making
      requests with `key=<key>` to decrement that particular counter. If no
      key is provided, 'default' is used.
    - **tries** - Specify the number of tries before success, as an integer. If
    no number is provided, you will get a success on the 3rd try.

    The server will let you know the key and how many tries are remaining until
    you get a successful response. Example error response:

    ```json
    HTTP/1.1 500 INTERNAL SERVER ERROR
    Content-Length: 116
    Content-Type: application/json
    Date: Wed, 19 Nov 2014 00:59:19 GMT
    Server: TwistedWeb/14.0.2

    {
        "error": "The server had an error. Try again 1 more time",
        "key": "foobar",
        "success": false,
        "tries_remaining": 1
    }
    ```

    Example usage:

    ```python
    r = requests.get('http://localhost:5512?key=special-key')
    assert_equal(r.status_code, 500)
    r = requests.get('http://localhost:5512?key=special-key')
    assert_equal(r.status_code, 500)
    # Third time is the charm
    r = requests.get('http://localhost:5512?key=special-key')
    assert_equal(r.status_code, 200)

    # Set tries=1 to serve a 200 right away.
    r = requests.get('http://localhost:5512?key=my-key&tries=1')
    assert_equal(r.status_code, 200)
    ```

    You can see the status of all available counters by making a GET request
    to `http://localhost:5512/counters`, or reset a counter by making a POST
    request to `http://localhost:5512/counters` with the `key` you want to
    reset.

- **5513** - Send a request to `localhost:5513?failrate=<float>`. The server
  will drop requests with a frequency of `failrate`.

- **5514** - The server will try as hard as it can to return a content type
that is not parseable by the `Accept` header provided by the request. Specify
a `Accept: application/json` header in your request and the server will return
data with the `text/morse` content type. The server will try these
content-types in turn:

- `text/morse`
- `application/json`
- `text/html`
- `text/csv`

If your Accept header indicates it can accept all of these content-types, the
server will return `text/morse`.

- **5515** - The server will return a response with a content-type that matches
the request, but it will be incomplete. The server will advertise an incorrect,
too long Content-Length, and the response body will not be complete. The
practical effect is that the server will hang halfway through the response
download. The server can return partial responses with the following
content-types:

- `application/json`
- `text/html`
- `text/plain`
- `text/xml`

If your server indicates an Accept header value of `*/*`, or the server cannot
find a matching content-type, the server will returnn an incomplete json
response.

- **5516** - Same semantics as port 5515, but the server will close the
connection partway through, instead of hanging indefinitely.

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

## Donating

Donations free up time to make improvements to the library, and respond to
bug reports. You can send donations via Paypal's "Send Money" feature to
kev@inburke.com. Donations are not tax deductible in the USA.
