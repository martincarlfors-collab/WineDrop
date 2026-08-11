"""Generera VAPID-nyckelpar för Web Push.

    pip install py-vapid
    python gen_vapid.py

Skriver ut en publik nyckel (till site/config.js) och en privat nyckel
(till hemligheten VAPID_PRIVATE). Publik nyckel används av både klient och server.
"""
from __future__ import annotations
import base64

try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
except ImportError:
    raise SystemExit("pip install cryptography")


def b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def main() -> None:
    key = ec.generate_private_key(ec.SECP256R1())

    priv_int = key.private_numbers().private_value
    priv = priv_int.to_bytes(32, "big")

    pub = key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )

    print("VAPID_PUBLIC (till site/config.js och VAPID_PUBLIC):")
    print("  " + b64url(pub))
    print("\nVAPID_PRIVATE (hemlig, till VAPID_PRIVATE):")
    print("  " + b64url(priv))


if __name__ == "__main__":
    main()
