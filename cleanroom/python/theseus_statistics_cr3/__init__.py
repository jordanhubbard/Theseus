"""
theseus_statistics_cr3 - Clean-room extended statistics utilities.
No imports of statistics, numpy, or scipy allowed.
"""

import math


class NormalDist:
    """Normal distribution with mean mu and standard deviation sigma."""
    
    def __init__(self, mu=0.0, sigma=1.0):
        if sigma < 0:
            raise ValueError("sigma must be non-negative")
        self._mu = float(mu)
        self._sigma = float(sigma)
    
    @property
    def mean(self):
        return self._mu
    
    @property
    def stdev(self):
        return self._sigma
    
    @property
    def variance(self):
        return self._sigma ** 2
    
    def pdf(self, x):
        """Probability density function at x."""
        if self._sigma == 0:
            raise ValueError("pdf undefined for sigma=0")
        variance = self._sigma ** 2
        exponent = -((x - self._mu) ** 2) / (2 * variance)
        coefficient = 1.0 / (self._sigma * math.sqrt(2 * math.pi))
        return coefficient * math.exp(exponent)
    
    def cdf(self, x):
        """Cumulative distribution function at x."""
        if self._sigma == 0:
            raise ValueError("cdf undefined for sigma=0")
        # Use the error function: CDF(x) = 0.5 * (1 + erf((x - mu) / (sigma * sqrt(2))))
        z = (x - self._mu) / (self._sigma * math.sqrt(2))
        return 0.5 * (1.0 + _erf(z))
    
    def inv_cdf(self, p):
        """Inverse cumulative distribution function (quantile function)."""
        if not (0 < p < 1):
            raise ValueError("p must be in (0, 1)")
        return self._mu + self._sigma * math.sqrt(2) * _erfinv(2 * p - 1)
    
    def overlap(self, other):
        """Compute the overlapping coefficient of two normal distributions."""
        # Bhattacharyya coefficient for normal distributions
        sigma1, sigma2 = self._sigma, other._sigma
        mu1, mu2 = self._mu, other._mu
        # Using the formula for overlap of two Gaussians
        # This is an approximation using numerical integration
        # For exact: use the analytical formula
        var1, var2 = sigma1**2, sigma2**2
        if var1 == 0 or var2 == 0:
            raise ValueError("overlap undefined for sigma=0")
        term1 = 0.25 * math.log(0.25 * (var1/var2 + var2/var1 + 2))
        term2 = 0.25 * (mu1 - mu2)**2 / (var1 + var2)
        return math.exp(-(term1 + term2))
    
    def __repr__(self):
        return f"NormalDist(mu={self._mu}, sigma={self._sigma})"
    
    def __eq__(self, other):
        if isinstance(other, NormalDist):
            return self._mu == other._mu and self._sigma == other._sigma
        return NotImplemented


def _erf(x):
    """Compute the error function erf(x) using a polynomial approximation."""
    # Abramowitz and Stegun approximation 7.1.26
    # Maximum error: 1.5e-7
    t = 1.0 / (1.0 + 0.3275911 * abs(x))
    poly = t * (0.254829592 +
                t * (-0.284496736 +
                     t * (1.421413741 +
                          t * (-1.453152027 +
                               t * 1.061405429))))
    result = 1.0 - poly * math.exp(-x * x)
    return result if x >= 0 else -result


def _erfinv(x):
    """Compute the inverse error function erfinv(x)."""
    # Using rational approximation
    if x == 0:
        return 0.0
    if abs(x) >= 1:
        raise ValueError("erfinv argument must be in (-1, 1)")
    
    # Approximation based on Peter J. Acklam's algorithm
    # for the inverse normal CDF, adapted for erfinv
    # erfinv(x) = invcdf((x+1)/2) / sqrt(2)
    p = (x + 1.0) / 2.0
    return _inv_normal_cdf(p) / math.sqrt(2)


def _inv_normal_cdf(p):
    """Inverse of the standard normal CDF using rational approximation."""
    # Coefficients for rational approximation
    # Peter J. Acklam's algorithm
    a = [-3.969683028665376e+01,  2.209460984245205e+02,
         -2.759285104469687e+02,  1.383577518672690e+02,
         -3.066479806614716e+01,  2.506628277459239e+00]
    b = [-5.447609879822406e+01,  1.615858368580409e+02,
         -1.556989798598866e+02,  6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
          4.374664141464968e+00,  2.938163982698783e+00]
    d = [7.784695709041462e-03,  3.224671290700398e-01,
         2.445134137142996e+00,  3.754408661907416e+00]
    
    p_low = 0.02425
    p_high = 1 - p_low
    
    if p < p_low:
        # Rational approximation for lower region
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p <= p_high:
        # Rational approximation for central region
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    else:
        # Rational approximation for upper region
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)


def geometric_mean(data):
    """
    Return the geometric mean of the data.
    geometric_mean(data) = (product of all values)^(1/n)
    """
    data = list(data)
    n = len(data)
    if n == 0:
        raise ValueError("geometric_mean requires at least one data point")
    
    for x in data:
        if x <= 0:
            raise ValueError("geometric_mean requires positive data")
    
    # Use logarithms to avoid overflow
    log_sum = sum(math.log(x) for x in data)
    return math.exp(log_sum / n)


def harmonic_mean(data):
    """
    Return the harmonic mean of the data.
    harmonic_mean(data) = n / sum(1/x for x in data)
    """
    data = list(data)
    n = len(data)
    if n == 0:
        raise ValueError("harmonic_mean requires at least one data point")
    
    for x in data:
        if x == 0:
            raise ValueError("harmonic_mean does not support zero values")
        if x < 0:
            raise ValueError("harmonic_mean does not support negative values")
    
    reciprocal_sum = sum(1.0 / x for x in data)
    return n / reciprocal_sum


def fmean(data):
    """
    Return the arithmetic mean of the data as a float.
    """
    data = list(data)
    n = len(data)
    if n == 0:
        raise ValueError("fmean requires at least one data point")
    return sum(data) / n


# --- Invariant test functions ---

def statistics3_normaldist():
    """Returns NormalDist(0, 1).mean which should be 0."""
    return NormalDist(0, 1).mean


def statistics3_geometric_mean():
    """Returns geometric_mean([4, 9]) which should be 6.0."""
    return geometric_mean([4, 9])


def statistics3_harmonic_mean():
    """Returns True if harmonic_mean([1, 2, 4]) ≈ 12/7."""
    result = harmonic_mean([1, 2, 4])
    expected = 12 / 7
    return abs(result - expected) < 1e-9


__all__ = [
    'NormalDist',
    'geometric_mean',
    'harmonic_mean',
    'fmean',
    'statistics3_normaldist',
    'statistics3_geometric_mean',
    'statistics3_harmonic_mean',
]