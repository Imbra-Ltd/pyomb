# Copyright (c) 2022-2026 Imbra Ltd
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Generate a throwaway certificate chain for testing Modbus TCP Security.

Run this to obtain a CA, a server certificate and role-bearing client
certificates for local TLS testing:

    py scripts/gen_test_certs.py

The output directory is gitignored. Generated keys are unencrypted and must
never be committed -- an earlier revision of this repository committed a CA
signing key and that material had to be treated as compromised, which is why
these are produced on demand rather than stored.

Requires the openssl executable on PATH. No Python dependencies, so the
package keeps its empty install_requires.
"""

import argparse
import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile

# Modbus role OID, per the MB-TCP-Security specification. The server reads the
# role from this extension to authorize a client.
ROLE_OID = "1.3.6.1.4.1.50316.802.1"

# One client certificate per role, mirroring the roles the specification names.
CLIENT_ROLES = ("operator", "engineer", "monitor")

DEFAULT_OUT = os.path.join("assets", "certificates")

CA_EXT = """
basicConstraints = critical, CA:TRUE, pathlen:0
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
"""

SERVER_EXT = """
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = critical, serverAuth
subjectAltName = DNS:localhost, IP:127.0.0.1
"""

# The role extension is what makes this a Modbus Security client certificate
# rather than a generic one. subjectAltName is absent by design: clients are
# authenticated by role, not by name.
CLIENT_EXT = """
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = critical, clientAuth
{oid} = ASN1:UTF8String:{role}
"""


def run(command):
    """Run a command, raising with captured output if it fails."""
    # This is the one place the script reaches openssl, and the two suppressed
    # checks -- the advisory on importing subprocess, and this call site --
    # both rest on the same property. command is always a list, which hands
    # the argument vector to the operating system directly rather than to a
    # shell, so an argument cannot break out and become a second command
    # however the caller spells a path. The checks match on call shape and
    # cannot see that the shell is absent.
    result = subprocess.run(command, capture_output=True, text=True)  # nosec B603

    if result.returncode != 0:
        raise RuntimeError("{} failed:\n{}".format(" ".join(command), result.stderr.strip()))

    return result


def write(path, text):
    """Write text to path, replacing whatever is there."""
    with open(path, "w") as handle:
        handle.write(text)


def make_ca(out, days, workdir):
    """Create the test certificate authority."""
    key = os.path.join(out, "ca.key")
    crt = os.path.join(out, "ca.crt")
    ext = os.path.join(workdir, "ca.ext")
    write(ext, CA_EXT)

    run(["openssl", "genrsa", "-out", key, "2048"])
    run(
        [
            "openssl",
            "req",
            "-new",
            "-x509",
            "-key",
            key,
            "-out",
            crt,
            "-days",
            str(days),
            "-sha256",
            "-subj",
            "/CN=pyomb test CA/O=Imbra Ltd",
            "-extensions",
            "v3_ca",
            "-config",
            ext_config(ext, "v3_ca"),
        ]
    )

    return key, crt


def ext_config(path, section):
    """Wrap a bare extension block in the minimal config openssl expects."""
    with open(path) as handle:
        body = handle.read()
    config = os.path.splitext(path)[0] + ".cnf"
    write(config, f"[req]\ndistinguished_name=dn\n[dn]\n[{section}]{body}")

    return config


def issue(out, name, subject, extension, ca_key, ca_crt, days, workdir):
    """Issue a certificate signed by the test CA."""
    key = os.path.join(out, name + ".key")
    crt = os.path.join(out, name + ".crt")
    csr = os.path.join(workdir, name + ".csr")
    ext = os.path.join(workdir, name + ".ext")
    write(ext, extension)

    run(["openssl", "genrsa", "-out", key, "2048"])
    run(["openssl", "req", "-new", "-key", key, "-out", csr, "-subj", subject])
    run(
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            csr,
            "-CA",
            ca_crt,
            "-CAkey",
            ca_key,
            "-CAcreateserial",
            "-out",
            crt,
            "-days",
            str(days),
            "-sha256",
            "-extfile",
            ext_config(ext, "ext"),
            "-extensions",
            "ext",
        ]
    )

    return key, crt


def main(argv: list[str] | None = None) -> int:
    """Mint the throwaway chain and return the process exit code.

    Args:
        argv (list[str] | None) : Command-line arguments, or None to read
            them from the process

    Returns:
        int : 0 on success, 1 where openssl is not on PATH
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=DEFAULT_OUT, help="output directory (default: %(default)s)")
    parser.add_argument("--days", type=int, default=365, help="validity in days (default: %(default)s)")
    args = parser.parse_args(argv)

    if shutil.which("openssl") is None:
        print("error: openssl not found on PATH", file=sys.stderr)
        return 1

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix="modbus-certs-")

    try:
        ca_key, ca_crt = make_ca(out, args.days, workdir)
        print("CA           ", os.path.relpath(ca_crt, os.getcwd()))

        issue(out, "server", "/CN=localhost/O=Imbra Ltd", SERVER_EXT, ca_key, ca_crt, args.days, workdir)
        print(
            "server       ",
            os.path.relpath(os.path.join(out, "server.crt"), os.getcwd()),
            "(SAN: localhost, 127.0.0.1)",
        )

        for role in CLIENT_ROLES:
            issue(
                out,
                "client-" + role,
                f"/CN=modbus client {role}/O=Imbra Ltd",
                CLIENT_EXT.format(oid=ROLE_OID, role=role.capitalize()),
                ca_key,
                ca_crt,
                args.days,
                workdir,
            )
            print(
                "client       ",
                os.path.relpath(os.path.join(out, "client-" + role + ".crt"), os.getcwd()),
                f"(role: {role.capitalize()})",
            )

    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print()
    print(f"Valid for {args.days} days. These are throwaway test credentials:")
    print("the keys are unencrypted and the directory is gitignored.")
    print("Never commit them, and never trust this CA outside a test network.")

    return 0


if __name__ == "__main__":
    # State the encoding rather than inheriting the console's, so what this
    # prints is what the reader sees on any machine.
    sys.stdout.reconfigure(encoding="utf-8")

    sys.exit(main())
