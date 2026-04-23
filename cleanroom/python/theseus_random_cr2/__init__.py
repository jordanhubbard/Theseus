import os
import math

def _get_random_bytes(n):
    return os.urandom(n)

def _random_float():
    """Return a random float in [0.0, 1.0]."""
    # Use 7 bytes (56 bits) for good precision
    raw = _get_random_bytes(7)
    val = int.from_bytes(raw, 'big')
    # 56 bits max value
    max_val = (1 << 56) - 1
    return val / max_val

def uniform(a, b):
    """Return a random float in [a, b]."""
    r = _random_float()
    return a + r * (b - a)

def gauss(mu, sigma):
    """Return a Gaussian deviate with mean mu and standard deviation sigma.
    Uses the Box-Muller transform.
    """
    # Box-Muller transform requires two uniform random numbers in (0, 1]
    # We use (0, 1] to avoid log(0)
    while True:
        u1 = _random_float()
        if u1 > 0.0:
            break
    while True:
        u2 = _random_float()
        if u2 > 0.0:
            break
    
    z0 = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z0

def randrange(stop):
    """Return a random integer in [0, stop)."""
    if stop <= 0:
        raise ValueError("stop must be positive")
    
    # Use rejection sampling to avoid modulo bias
    # Find the smallest number of bytes needed
    num_bytes = (stop.bit_length() + 7) // 8
    if num_bytes == 0:
        num_bytes = 1
    
    max_val = 1 << (num_bytes * 8)
    # Largest multiple of stop that fits in max_val
    limit = max_val - (max_val % stop)
    
    while True:
        raw = _get_random_bytes(num_bytes)
        val = int.from_bytes(raw, 'big')
        if val < limit:
            return val % stop

def random2_uniform():
    """Test: 0.0 <= uniform(0, 1) <= 1.0"""
    result = uniform(0, 1)
    return 0.0 <= result <= 1.0

def random2_randrange():
    """Test: randrange(10) in range(10)"""
    result = randrange(10)
    return result in range(10)

def random2_gauss_type():
    """Test: isinstance(gauss(0, 1), float)"""
    result = gauss(0, 1)
    return isinstance(result, float)