"""ViGo Standard Library: Scientific Computing (scilib)
Provides statistics, linear algebra, matrix operations, and numerical methods.
Pure Python — no third-party dependencies.
"""
import math
import random
from ..runtime.objects import BuiltinFunction


def register(env):
    """Register all scilib functions into the given ViGo environment."""

    # ── Statistics ──

    def mean(data):
        """Return the arithmetic mean of a list of numbers."""
        if not data:
            return 0
        return sum(data) / len(data)

    def median(data):
        """Return the median of a list of numbers."""
        if not data:
            return 0
        sorted_data = sorted(data)
        n = len(sorted_data)
        if n % 2 == 1:
            return sorted_data[n // 2]
        return (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2

    def mode(data):
        """Return the most frequent value in a list."""
        if not data:
            return None
        freq = {}
        for v in data:
            freq[v] = freq.get(v, 0) + 1
        max_count = max(freq.values())
        for k, v in freq.items():
            if v == max_count:
                return k

    def variance(data, sample=True):
        """Return the variance of a list. Set sample=False for population variance."""
        if not data or len(data) < 2:
            return 0
        m = mean(data)
        n = len(data)
        divisor = n - 1 if sample else n
        return sum((x - m) ** 2 for x in data) / divisor

    def stdev(data, sample=True):
        """Return the standard deviation. Set sample=False for population stdev."""
        return math.sqrt(variance(data, sample))

    def percentile(data, p):
        """Return the p-th percentile (0-100) of a list."""
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (p / 100) * (len(sorted_data) - 1)
        f = int(k)
        c = k - f
        if f + 1 < len(sorted_data):
            return sorted_data[f] + c * (sorted_data[f + 1] - sorted_data[f])
        return sorted_data[f]

    def covariance(x, y):
        """Return the covariance between two lists of equal length."""
        if not x or not y or len(x) != len(y):
            return 0
        mx, my = mean(x), mean(y)
        return sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / (len(x) - 1)

    def correlation(x, y):
        """Return the Pearson correlation coefficient between two lists."""
        if not x or not y or len(x) != len(y):
            return 0
        sx, sy = stdev(x), stdev(y)
        if sx == 0 or sy == 0:
            return 0
        return covariance(x, y) / (sx * sy)

    def linreg(x, y):
        """Simple linear regression. Returns (slope, intercept)."""
        if not x or not y or len(x) != len(y) or len(x) < 2:
            return (0, 0)
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)
        denom = n * sum_x2 - sum_x ** 2
        if denom == 0:
            return (0, 0)
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
        return (slope, intercept)

    # ── Vector operations ──

    def vec_add(a, b):
        """Element-wise vector addition."""
        return [ai + bi for ai, bi in zip(a, b)]

    def vec_sub(a, b):
        """Element-wise vector subtraction."""
        return [ai - bi for ai, bi in zip(a, b)]

    def vec_scale(a, scalar):
        """Scalar multiplication of a vector."""
        return [ai * scalar for ai in a]

    def dot_product(a, b):
        """Dot product of two vectors."""
        return sum(ai * bi for ai, bi in zip(a, b))

    def cross_product(a, b):
        """Cross product of two 3D vectors."""
        if len(a) != 3 or len(b) != 3:
            raise ValueError("Cross product requires 3D vectors")
        return [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        ]

    def norm(a, p=2):
        """Vector norm. p=2 for Euclidean, p=1 for Manhattan, p=0 for infinity."""
        if p == 0:
            return max(abs(xi) for xi in a)
        if p == 1:
            return sum(abs(xi) for xi in a)
        return math.sqrt(sum(xi ** 2 for xi in a))

    def normalize(a):
        """Return a unit vector in the same direction."""
        n = norm(a)
        if n == 0:
            return [0] * len(a)
        return [xi / n for xi in a]

    # ── Matrix operations ──

    def matrix_create(rows, cols, fill=0):
        """Create a rows x cols matrix filled with a value."""
        return [[fill for _ in range(cols)] for _ in range(rows)]

    def matrix_identity(n):
        """Create an n x n identity matrix."""
        m = matrix_create(n, n, 0)
        for i in range(n):
            m[i][i] = 1
        return m

    def matrix_shape(m):
        """Return (rows, cols) of a matrix."""
        if not m:
            return (0, 0)
        return (len(m), len(m[0]) if m[0] else 0)

    def matrix_multiply(a, b):
        """Multiply two matrices a (m x n) and b (n x p)."""
        if not a or not b:
            return []
        m, n = matrix_shape(a)
        n2, p = matrix_shape(b)
        if n != n2:
            raise ValueError(f"Matrix shape mismatch: ({m},{n}) x ({n2},{p})")
        result = matrix_create(m, p, 0)
        for i in range(m):
            for j in range(p):
                total = 0
                for k in range(n):
                    total += a[i][k] * b[k][j]
                result[i][j] = total
        return result

    def matrix_transpose(m):
        """Transpose a matrix."""
        if not m:
            return []
        rows, cols = matrix_shape(m)
        result = matrix_create(cols, rows, 0)
        for i in range(rows):
            for j in range(cols):
                result[j][i] = m[i][j]
        return result

    def matrix_determinant(m):
        """Compute the determinant of a square matrix (recursive)."""
        if not m:
            return 0
        n = len(m)
        if n == 1:
            return m[0][0]
        if n == 2:
            return m[0][0] * m[1][1] - m[0][1] * m[1][0]
        det = 0
        for j in range(n):
            sub = [[m[r][c] for c in range(n) if c != j] for r in range(1, n)]
            det += ((-1) ** j) * m[0][j] * matrix_determinant(sub)
        return det

    def matrix_inverse(m):
        """Compute the inverse of a square matrix (Gauss-Jordan)."""
        n = len(m)
        aug = [row[:] + [1 if i == j else 0 for j in range(n)] for i, row in enumerate(m)]
        for i in range(n):
            if aug[i][i] == 0:
                for k in range(i + 1, n):
                    if aug[k][i] != 0:
                        aug[i], aug[k] = aug[k], aug[i]
                        break
                else:
                    raise ValueError("Matrix is singular")
            pivot = aug[i][i]
            for j in range(2 * n):
                aug[i][j] /= pivot
            for k in range(n):
                if k != i:
                    factor = aug[k][i]
                    for j in range(2 * n):
                        aug[k][j] -= factor * aug[i][j]
        return [row[n:] for row in aug]

    def matrix_solve(a, b):
        """Solve linear system Ax = b using matrix inversion."""
        inv_a = matrix_inverse(a)
        return [sum(inv_a[i][j] * b[j] for j in range(len(b))) for i in range(len(a))]

    # ── Numerical methods ──

    def derivative(f, x, h=1e-6):
        """Numerical derivative of f at x using central difference."""
        return (f(x + h) - f(x - h)) / (2 * h)

    def integral_simpson(f, a, b, n=100):
        """Numerical integration using Simpson's rule. n must be even."""
        if n % 2 == 1:
            n += 1
        h = (b - a) / n
        total = f(a) + f(b)
        for i in range(1, n):
            xi = a + i * h
            total += 4 * f(xi) if i % 2 == 1 else 2 * f(xi)
        return total * h / 3

    def integral_trapezoid(f, a, b, n=100):
        """Numerical integration using the trapezoidal rule."""
        h = (b - a) / n
        total = (f(a) + f(b)) / 2
        for i in range(1, n):
            total += f(a + i * h)
        return total * h

    def gradient_descent(f_grad, x0, lr=0.01, max_iter=1000, tol=1e-6):
        """Gradient descent optimization."""
        x = list(x0)
        for i in range(max_iter):
            grad = f_grad(x)
            step = [lr * g for g in grad]
            if math.sqrt(sum(s ** 2 for s in step)) < tol:
                return (x, i + 1)
            x = [xi - si for xi, si in zip(x, step)]
        return (x, max_iter)

    def newton_method(f, f_prime, x0, max_iter=100, tol=1e-6):
        """Newton's method for root-finding."""
        x = x0
        for i in range(max_iter):
            fx = f(x)
            fpx = f_prime(x)
            if abs(fpx) < 1e-12:
                raise ValueError("Derivative too close to zero")
            x_new = x - fx / fpx
            if abs(x_new - x) < tol:
                return (x_new, i + 1)
            x = x_new
        return (x, max_iter)

    # ── Registration ──

    env.define("mean", BuiltinFunction(mean, "mean"))
    env.define("median", BuiltinFunction(median, "median"))
    env.define("mode", BuiltinFunction(mode, "mode"))
    env.define("variance", BuiltinFunction(variance, "variance"))
    env.define("stdev", BuiltinFunction(stdev, "stdev"))
    env.define("percentile", BuiltinFunction(percentile, "percentile"))
    env.define("covariance", BuiltinFunction(covariance, "covariance"))
    env.define("correlation", BuiltinFunction(correlation, "correlation"))
    env.define("linreg", BuiltinFunction(linreg, "linreg"))
    env.define("vec_add", BuiltinFunction(vec_add, "vec_add"))
    env.define("vec_sub", BuiltinFunction(vec_sub, "vec_sub"))
    env.define("vec_scale", BuiltinFunction(vec_scale, "vec_scale"))
    env.define("dot_product", BuiltinFunction(dot_product, "dot_product"))
    env.define("cross_product", BuiltinFunction(cross_product, "cross_product"))
    env.define("norm", BuiltinFunction(norm, "norm"))
    env.define("normalize", BuiltinFunction(normalize, "normalize"))
    env.define("matrix_create", BuiltinFunction(matrix_create, "matrix_create"))
    env.define("matrix_identity", BuiltinFunction(matrix_identity, "matrix_identity"))
    env.define("matrix_shape", BuiltinFunction(matrix_shape, "matrix_shape"))
    env.define("matrix_multiply", BuiltinFunction(matrix_multiply, "matrix_multiply"))
    env.define("matrix_transpose", BuiltinFunction(matrix_transpose, "matrix_transpose"))
    env.define("matrix_determinant", BuiltinFunction(matrix_determinant, "matrix_determinant"))
    env.define("matrix_inverse", BuiltinFunction(matrix_inverse, "matrix_inverse"))
    env.define("matrix_solve", BuiltinFunction(matrix_solve, "matrix_solve"))
    env.define("derivative", BuiltinFunction(derivative, "derivative"))
    env.define("integral_simpson", BuiltinFunction(integral_simpson, "integral_simpson"))
    env.define("integral_trapezoid", BuiltinFunction(integral_trapezoid, "integral_trapezoid"))
    env.define("gradient_descent", BuiltinFunction(gradient_descent, "gradient_descent"))
    env.define("newton_method", BuiltinFunction(newton_method, "newton_method"))