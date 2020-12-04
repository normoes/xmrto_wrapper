import sys
from random import getrandbits
from ipaddress import IPv4Address, IPv6Address


def get_random_ip_address(ip_version=4):
    if ip_version == 4:
        bits = getrandbits(32)  # generates an integer with 32 random bits
        addr = IPv4Address(
            bits
        )  # instances an IPv4Address object from those bits
        addr_str = str(
            addr
        )  # get the IPv4Address object's string representation
    elif ip_version == 6:
        bits = getrandbits(128)  # generates an integer with 128 random bits
        addr = IPv6Address(
            bits
        )  # instances an IPv6Address object from those bits
        # .compressed contains the short version of the IPv6 address
        # str(addr) always returns the short address
        # .exploded is the opposite of this, always returning the full address with all-zero groups and so on
        addr_str = addr.compressed

    return addr_str


def main():
    print("4")
    print(get_random_ip_address(ip_version=4))
    print("6")
    print(get_random_ip_address(6))
    print("4")
    print(get_random_ip_address())


if __name__ == "__main__":
    sys.exit(main())
