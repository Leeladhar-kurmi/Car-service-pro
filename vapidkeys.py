from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from base64 import urlsafe_b64encode

# Generate a new EC (Elliptic Curve) private key
private_key = ec.generate_private_key(ec.SECP256R1())

# Get the private key in PEM format (if you want to store it securely)
pem_private = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

# Get the public key
public_key = private_key.public_key()

# Convert public key to bytes
raw_public = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

# Base64 encode both keys (URL safe)
vapid_private_key = urlsafe_b64encode(
    private_key.private_numbers().private_value.to_bytes(32, 'big')
).decode('utf-8')

vapid_public_key = urlsafe_b64encode(raw_public).decode('utf-8')

print("VAPID PUBLIC KEY:", vapid_public_key)
print("VAPID PRIVATE KEY:", vapid_private_key)
