"""Drive the client and server simulators against each other.

Both simulators exist to exercise something else -- point the client at a real
device, or the server at a real master -- so running them against each other is
mostly a way to see the shape of an exchange before wiring one up in anger.

The request reads 10 coils, which the server answers with two data bytes: eight
coils in the first and two in the second, so the count is bytes rather than
coils and the last byte is only partly meaningful.

The README shows port 502, the registered Modbus port a real device listens on.
This asks for a free port instead, which is what lets the file run without
privileges on any machine.
"""

from pyomb import ModbusClientSimulator, ModbusServerSimulator

# Seconds to wait for the listener. Bounded rather than blocking, so a startup
# failure reports itself instead of hanging with the reason on stderr.
TIMEOUT = 10.0

NO_LISTENER = "the server never reached its accept loop"


def main() -> None:
    """Start both simulators, read 10 coils, and shut them down."""
    server = ModbusServerSimulator(port=0)
    server.daemon = True
    server.start()

    if not server.started_event.wait(TIMEOUT):
        raise SystemExit(NO_LISTENER)

    print(f"server listening on port {server.port}")

    client = ModbusClientSimulator(port=server.port)

    try:
        client.connect()

        try:
            header, pdu = client.request(fc=1, read_address=0, read_count=10)

            print(header)
            print(pdu)

        finally:
            client.disconnect()

    finally:
        server.stop()
        server.join(TIMEOUT)


if __name__ == "__main__":
    main()
