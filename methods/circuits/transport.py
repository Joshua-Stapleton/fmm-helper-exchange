"""Exact helper transfer between row-coordinate bases, with no free conversion claim."""
from fractions import Fraction as Q
from lrp import inv, matmul

def transport(forms, old_boundary, new_boundary):
    """For x_old=C_old*x and x_new=C_new*x, map v to v*C_old*C_new^-1."""
    pull = matmul(old_boundary, inv(new_boundary))
    return matmul([[Q(x) for x in v] for v in forms], pull)
