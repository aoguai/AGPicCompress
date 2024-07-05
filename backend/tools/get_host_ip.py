import socket


def host_ip():
    """
    Get the IP address of the host machine.
    :return: IP address
    """
    default_ip = '0.0.0.0'
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except OSError:
        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname)
        except socket.error:
            ip = default_ip
    finally:
        s.close()

    return ip
